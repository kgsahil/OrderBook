"""Broadcast utilities for websocket messages."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from message_models import (
    AgentsSnapshotMessage,
    InstrumentsMessage,
    OrderBookMessage,
    OrderPlacedMessage,
)
from state import (
    agent_manager,
    instrument_service,
    market_maker_service,
    ob_client,
    portfolio_tracker,
    regular_connections,
)

# Global sequence counter for orderbook broadcasts
_broadcast_sequence = 0
_sequence_lock = asyncio.Lock()


async def _get_next_sequence() -> int:
    """Get next sequence number for orderbook broadcast."""
    global _broadcast_sequence
    async with _sequence_lock:
        _broadcast_sequence += 1
        return _broadcast_sequence


async def _send_to_dashboards(payload: dict):
    """Send payload to all connected dashboard clients."""
    if not regular_connections:
        return
    disconnected: List[WebSocket] = []
    message = json.dumps(payload)
    for connection in list(regular_connections):
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)
    for connection in disconnected:
        regular_connections.discard(connection)


async def _send_to_agents(payload: dict):
    """Send payload to all connected agents."""
    message = json.dumps(payload)
    for agent_id in agent_manager.get_all_agent_ids():
        ws = agent_manager.get_websocket(agent_id)
        if ws:
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError, ConnectionError):
                pass
            except Exception as e:
                logger.warning(f"Unexpected error sending to agent {agent_id}: {e}")


async def broadcast_instruments_update():
    instruments = instrument_service.list_instruments()
    instrument_models = [
        instrument.to_dict() for instrument in instruments
    ]
    message = InstrumentsMessage(data=instrument_models).model_dump()
    await _send_to_dashboards(message)
    await _send_to_agents(message)
    await broadcast_orderbook_snapshots([inst.symbol_id for inst in instruments])


async def broadcast_orderbook_snapshots(symbol_ids: Optional[Iterable[int]] = None):
    """Broadcast snapshots for specific instruments (or all if None)."""
    if symbol_ids:
        target_ids = list({int(sid) for sid in symbol_ids})
    else:
        target_ids = [inst.symbol_id for inst in instrument_service.list_instruments()]

    if not target_ids:
        return

    snapshots: Dict[int, dict] = {}
    current_prices: Dict[int, float] = {}
    for symbol_id in target_ids:
        snapshot = ob_client.get_snapshot(symbol_id)
        if snapshot.get("status") == "success":
            snapshots[symbol_id] = snapshot
            bids = snapshot.get("bids", [])
            asks = snapshot.get("asks", [])
            if bids and asks:
                mid_price = (bids[0]["price"] + asks[0]["price"]) / 2
                current_prices[symbol_id] = mid_price
            elif bids:
                current_prices[symbol_id] = bids[0]["price"]
            elif asks:
                current_prices[symbol_id] = asks[0]["price"]

    if current_prices:
        portfolio_tracker.update_portfolio_values(current_prices)

    if snapshots:
        # Add sequence number and timestamp for tracking
        sequence = await _get_next_sequence()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        message = OrderBookMessage(
            data=snapshots,
            sequence=sequence,
            timestamp=timestamp
        ).model_dump()
        await _send_to_dashboards(message)
        await _send_to_agents(message)


async def broadcast_agents_snapshot():
    agents = [agent.to_dict() for agent in agent_manager.list_agents()]
    message = AgentsSnapshotMessage(data=agents).model_dump()
    await _send_to_dashboards(message)


async def broadcast_order_event(payload: OrderPlacedMessage):
    data = payload.model_dump()
    await _send_to_dashboards(data)


async def broadcast_news_update(news_payload: dict):
    payload = {
        "type": "news",
        "version": 1,
        "data": news_payload,
    }
    await _send_to_dashboards(payload)
    await _send_to_agents(payload)


async def broadcast_agent_created(agent_data: dict):
    """Broadcast when a new agent is created (e.g., from UI)."""
    payload = {
        "type": "agent_created",
        "data": agent_data,
    }
    # Send to all connections (both dashboards and potential agent services)
    message = json.dumps(payload)
    disconnected: List[WebSocket] = []
    for connection in list(regular_connections):
        try:
            await connection.send_text(message)
        except (WebSocketDisconnect, RuntimeError, ConnectionError):
            disconnected.append(connection)
        except Exception as e:
            logger.warning(f"Unexpected error broadcasting agent_created: {e}")
            disconnected.append(connection)
    for connection in disconnected:
        regular_connections.discard(connection)
    # Also send to already connected agents (for awareness)
    await _send_to_agents(payload)
