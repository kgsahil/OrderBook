# pylint: disable=duplicate-code
"""FastAPI application that bridges dashboards/agents with the C++ order book."""

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from broadcast import (
    broadcast_agents_snapshot,
    broadcast_instruments_update,
    broadcast_order_event,
    broadcast_orderbook_snapshots,
)
from message_models import OrderPlacedMessage, OrderPlacedPayload
from routers import agents as agents_router
from routers import instruments as instruments_router
from routers import news as news_router
from routers import performance as performance_router
from state import (
    DEFAULT_INSTRUMENT,
    agent_manager,
    instrument_service,
    market_maker_service,
    news_service,
    portfolio_tracker,
    regular_connections,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Performance metrics tracking
class PerformanceMetrics:
    """Track orderbook performance metrics."""
    
    def __init__(self):
        self.trade_timestamps = deque(maxlen=1000)  # Last 1000 trades
        self.order_timestamps = deque(maxlen=1000)  # Last 1000 orders
        self.queue_full_count = 0
        self.total_orders = 0
        self.total_trades = 0
        self.total_volume = 0.0
        self.start_time = time.time()
        # SPSC queue capacity (from constants.hpp)
        self.queue_capacity = 1024  # DEFAULT_QUEUE_SIZE
        
    def record_order(self, quantity: float = 0):
        """Record an order submission."""
        self.order_timestamps.append(time.time())
        self.total_orders += 1
        if quantity > 0:
            self.total_volume += quantity
            
    def record_trade(self, quantity: float = 0):
        """Record a trade execution."""
        self.trade_timestamps.append(time.time())
        self.total_trades += 1
        if quantity > 0:
            self.total_volume += quantity
            
    def record_queue_full(self):
        """Record when queue is full."""
        self.queue_full_count += 1
        
    def get_trades_per_second(self, window_seconds: float = 1.0) -> float:
        """Calculate trades per second over a time window."""
        if not self.trade_timestamps:
            return 0.0
        now = time.time()
        cutoff = now - window_seconds
        recent_trades = sum(1 for ts in self.trade_timestamps if ts > cutoff)
        return recent_trades / window_seconds
        
    def get_orders_per_second(self, window_seconds: float = 1.0) -> float:
        """Calculate orders per second over a time window."""
        if not self.order_timestamps:
            return 0.0
        now = time.time()
        cutoff = now - window_seconds
        recent_orders = sum(1 for ts in self.order_timestamps if ts > cutoff)
        return recent_orders / window_seconds
        
    def get_stats(self) -> Dict:
        """Get current performance statistics."""
        uptime = time.time() - self.start_time
        return {
            "trades_per_second": round(self.get_trades_per_second(), 2),
            "orders_per_second": round(self.get_orders_per_second(), 2),
            "total_trades": self.total_trades,
            "total_orders": self.total_orders,
            "total_volume": round(self.total_volume, 2),
            "queue_full_count": self.queue_full_count,
            "queue_capacity": self.queue_capacity,
            "queue_usage_pct": min(100, round((self.queue_full_count / max(1, self.total_orders)) * 100, 2)),
            "uptime_seconds": round(uptime, 2),
            "avg_trades_per_second": round(self.total_trades / max(1, uptime), 2),
            "avg_orders_per_second": round(self.total_orders / max(1, uptime), 2),
        }

# Global performance metrics instance
performance_metrics = PerformanceMetrics()

app = FastAPI(title="Trading Simulation Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(instruments_router.router)
app.include_router(agents_router.router)
app.include_router(news_router.router)
# Set performance metrics instance before including router
performance_router.set_performance_metrics(performance_metrics)
app.include_router(performance_router.router)


async def periodic_sync():
    """Occasional broadcast to keep dashboards aligned."""
    while True:
        await asyncio.sleep(5.0)
        await broadcast_orderbook_snapshots()
        await broadcast_agents_snapshot()


@app.on_event("startup")
async def startup_event():
    """Bootstrap default instrument and start background jobs."""
    instruments = instrument_service.list_instruments()
    if not instruments:
        logger.info(
            "No instruments detected on startup. Adding default instrument %s",
            DEFAULT_INSTRUMENT.ticker,
        )
        default_inst = instrument_service.add_instrument(
            DEFAULT_INSTRUMENT.ticker,
            DEFAULT_INSTRUMENT.description,
            DEFAULT_INSTRUMENT.industry,
            DEFAULT_INSTRUMENT.initial_price,
        )
        if default_inst:
            instruments = instrument_service.list_instruments()
            await broadcast_instruments_update()
        else:
            logger.error(
                "Failed to create default instrument; system will remain without instruments."
            )

    market_maker_service.set_book_update_callback(broadcast_orderbook_snapshots)
    asyncio.create_task(periodic_sync())
    asyncio.create_task(market_maker_service.bootstrap(instruments))


async def _send_initial_payloads(websocket: WebSocket):
    instruments = instrument_service.list_instruments()
    await websocket.send_text(
        json.dumps({"type": "instruments", "data": [inst.to_dict() for inst in instruments]})
    )

    orderbook_snapshots = {}
    for instrument in instruments:
        snapshot = instrument_service.client.get_snapshot(instrument.symbol_id)
        if snapshot.get("status") == "success":
            orderbook_snapshots[instrument.symbol_id] = snapshot
    if orderbook_snapshots:
        await websocket.send_text(json.dumps({"type": "orderbooks", "data": orderbook_snapshots}))

    all_news = news_service.get_news()
    if all_news:
        await websocket.send_text(
            json.dumps({"type": "news_history", "data": [news.to_dict() for news in all_news]})
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboards and agents."""
    await websocket.accept()
    regular_connections.add(websocket)
    logger.info("Client connected. Total connections: %s", len(regular_connections))

    try:
        await _send_initial_payloads(websocket)
        await broadcast_agents_snapshot()

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from client: {e}, data: {data[:200]}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                continue

            if message.get("type") != "agent_register" and message.get("type") not in [
                "add_order", "cancel_order", "get_portfolio", "agent_register"
            ]:
                logger.warning(f"Unknown message type: {message.get('type')}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}"
                }))
                continue

            if message["type"] == "agent_register":
                regular_connections.discard(websocket)
                agent_id = message.get("agent_id", str(uuid.uuid4()))
                name = message.get("name", f"Agent_{agent_id[:8]}")
                personality = message.get("personality", "neutral")
                starting_capital = message.get("starting_capital", 100000.0)

                agent = agent_manager.register_agent(
                    agent_id, name, personality, starting_capital, websocket
                )

                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "agent_registered",
                            "agent_id": agent_id,
                            "agent": agent.to_dict(),
                        }
                    )
                )
                await _send_initial_payloads(websocket)
                await broadcast_agents_snapshot()
                continue

            if message["type"] == "add_order":
                symbol_id = message.get("symbol_id", 1)
                side = message.get("side", "").upper()
                order_type = message.get("orderType", "LIMIT").upper()
                
                # Validate side
                if side not in ("BUY", "SELL"):
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid side: must be 'buy' or 'sell', got '{message.get('side')}'"}
                    }))
                    continue
                
                # Validate order type
                if order_type not in ("LIMIT", "MARKET"):
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid order type: must be 'LIMIT' or 'MARKET', got '{message.get('orderType')}'"}
                    }))
                    continue
                
                # Validate quantity
                quantity = message.get("quantity")
                try:
                    quantity = float(quantity)
                    if quantity <= 0 or not isinstance(quantity, (int, float)):
                        raise ValueError("Quantity must be a positive number")
                except (TypeError, ValueError) as e:
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid quantity: {e}"}
                    }))
                    continue
                
                # Validate price for LIMIT orders
                price = message.get("price")
                if order_type == "LIMIT":
                    if price is None:
                        await websocket.send_text(json.dumps({
                            "type": "order_response",
                            "data": {"status": "error", "message": "Price is required for LIMIT orders"}
                        }))
                        continue
                    try:
                        price = float(price)
                        if price <= 0:
                            raise ValueError("Price must be positive for LIMIT orders")
                    except (TypeError, ValueError) as e:
                        await websocket.send_text(json.dumps({
                            "type": "order_response",
                            "data": {"status": "error", "message": f"Invalid price for LIMIT order: {e}"}
                        }))
                        continue
                else:
                    # MARKET orders don't need price, set to 0
                    price = 0
                
                agent_id = message.get("agent_id")

                result = instrument_service.client.add_order(
                    symbol_id, side, order_type, price, quantity
                )
                # Track performance metrics
                if result.get("status") == "success":
                    performance_metrics.record_order(quantity)
                elif "QUEUE_FULL" in str(result.get("message", "")):
                    performance_metrics.record_queue_full()

                if result["status"] == "success" and agent_id:
                    agent = agent_manager.get_agent(agent_id)
                    instrument = instrument_service.get_instrument(symbol_id)
                    if agent:
                        try:
                            portfolio_tracker.record_trade(
                                agent_id, symbol_id, side.lower(), price, int(quantity)
                            )
                            # Track trade in performance metrics
                            performance_metrics.record_trade(quantity)
                            await broadcast_agents_snapshot()
                        except (ValueError, TypeError, KeyError) as exc:
                            logger.error("Error recording trade: %s", exc)
                        except Exception as exc:  # pragma: no cover
                            logger.exception("Unexpected error recording trade: %s", exc)

                    order_message = OrderPlacedMessage(
                        data=OrderPlacedPayload(
                            agent_id=agent_id,
                            agent_name=agent.name if agent else "Unknown",
                            symbol_id=symbol_id,
                            ticker=instrument.ticker if instrument else f"SYM{symbol_id}",
                            side=side,
                            order_type=order_type,
                            price=price,
                            quantity=quantity,
                            timestamp=datetime.now().isoformat(),
                        )
                    )
                    await broadcast_order_event(order_message)

                await broadcast_orderbook_snapshots([symbol_id])
                await websocket.send_text(
                    json.dumps({"type": "order_response", "data": result})
                )
                continue

            if message["type"] == "cancel_order":
                symbol_id = message.get("symbol_id", 1)
                order_id = message["orderId"]
                result = instrument_service.client.cancel_order(symbol_id, order_id)
                await websocket.send_text(
                    json.dumps({"type": "cancel_response", "data": result})
                )
                if result.get("status") == "success":
                    await broadcast_orderbook_snapshots([symbol_id])
                continue

            if message["type"] == "get_portfolio":
                agent_id = message.get("agent_id")
                if agent_id:
                    agent = agent_manager.get_agent(agent_id)
                    if agent:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "portfolio_update",
                                    "cash": agent.cash,
                                    "positions": {
                                        k: v.to_dict() for k, v in agent.positions.items()
                                    },
                                    "total_value": agent.total_value,
                                    "pnl": agent.pnl,
                                }
                            )
                        )
                continue

    except WebSocketDisconnect:
        regular_connections.discard(websocket)
        agent_manager.unregister_websocket(websocket)
        logger.info(
            "Client disconnected. Total connections: %s", len(regular_connections)
        )
        await broadcast_agents_snapshot()
    except Exception as exc:  # pragma: no cover
        logger.exception("WebSocket error: %s", exc)
        regular_connections.discard(websocket)
        agent_manager.unregister_websocket(websocket)
        await broadcast_agents_snapshot()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "connections": len(regular_connections),
        "agents": len(agent_manager.get_all_agent_ids()),
        "instruments": len(instrument_service.list_instruments()),
    }


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# C++ backend connection settings
CPP_HOST = "localhost"
CPP_PORT = 9999

# Global orderbook client
ob_client = OrderBookClient(CPP_HOST, CPP_PORT)

# Default bootstrap instrument (ensures dashboard/agents have something to trade)
DEFAULT_BOOTSTRAP_INSTRUMENT = {
    "ticker": os.getenv("DEFAULT_INSTRUMENT_TICKER", "AAPL"),
    "description": os.getenv("DEFAULT_INSTRUMENT_DESC", "Apple Inc."),
    "industry": os.getenv("DEFAULT_INSTRUMENT_INDUSTRY", "Technology"),
    "initial_price": float(os.getenv("DEFAULT_INSTRUMENT_PRICE", "150.0"))
}

# Services
instrument_service = InstrumentService(ob_client)
agent_manager = AgentManager()
portfolio_tracker = PortfolioTracker(agent_manager)
news_service = NewsService()
market_maker_service = MarketMakerService(ob_client)

# Regular WebSocket clients (non-agent)
regular_connections: Set[WebSocket] = set()


async def broadcast_to_regular_clients(payload: Dict[str, Any]):
    """Broadcast a payload to all dashboard clients."""
    if not regular_connections:
        return
    
    message = json.dumps(payload)
    disconnected: Set[WebSocket] = set()
    
    for connection in list(regular_connections):
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.add(connection)
    
    regular_connections.difference_update(disconnected)


async def broadcast_to_agents(payload: Dict[str, Any]):
    """Broadcast a payload to all connected agents."""
    message = json.dumps(payload)
    
    for agent_id in agent_manager.get_all_agent_ids():
        ws = agent_manager.get_websocket(agent_id)
        if ws:
            try:
                await ws.send_text(message)
            except Exception:
                pass


async def broadcast_instruments_update():
    """Broadcast refreshed instrument list and orderbook snapshots to dashboards and agents."""
    instruments = instrument_service.list_instruments()
    
    # Send instruments list
    payload = {
        "type": "instruments",
        "data": [inst.to_dict() for inst in instruments]
    }
    await broadcast_to_regular_clients(payload)
    await broadcast_to_agents(payload)
    
    # Also push snapshots so everyone has immediate book state
    await broadcast_orderbook_snapshots([inst.symbol_id for inst in instruments])


async def broadcast_orderbook_snapshots(symbol_ids: Optional[List[int]] = None):
    """Broadcast snapshots for specific instruments (or all if None)."""
    target_ids: List[int]
    if symbol_ids:
        target_ids = list({int(sid) for sid in symbol_ids})
    else:
        target_ids = [inst.symbol_id for inst in instrument_service.list_instruments()]
    
    if not target_ids:
        return
    
    snapshots: Dict[int, Any] = {}
    for symbol_id in target_ids:
        snapshot = ob_client.get_snapshot(symbol_id)
        if snapshot.get("status") == "success":
            snapshots[symbol_id] = snapshot
    
    if snapshots:
        payload = {
            "type": "orderbooks",
            "data": snapshots
        }
        await broadcast_to_regular_clients(payload)
        await broadcast_to_agents(payload)


async def broadcast_news_update(news: News):
    """Broadcast a single news item to dashboards and agents."""
    payload = {
        "type": "news",
        "data": news.to_dict()
    }
    await broadcast_to_regular_clients(payload)
    await broadcast_to_agents(payload)


async def broadcast_agents_snapshot():
    """Broadcast the latest agent stats to dashboards."""
    agents = agent_manager.list_agents()
    payload = {
        "type": "agents_snapshot",
        "data": [agent.to_dict() for agent in agents]
    }
    await broadcast_to_regular_clients(payload)

# Let market maker push updates whenever it refreshes liquidity
market_maker_service.set_book_update_callback(broadcast_orderbook_snapshots)
async def broadcast_orderbooks():
    """Fallback periodic broadcast to resync any missed clients."""
    BROADCAST_INTERVAL = float(os.getenv("BROADCAST_INTERVAL", "5.0"))  # Slow fallback sync
    
    while True:
        try:
            await asyncio.sleep(BROADCAST_INTERVAL)
            
            instruments = instrument_service.list_instruments()
            if not instruments:
                continue
            
            # Get snapshots for all instruments
            snapshots = {}
            current_prices = {}
            
            for instrument in instruments:
                snapshot = ob_client.get_snapshot(instrument.symbol_id)
                if snapshot["status"] == "success":
                    snapshots[instrument.symbol_id] = snapshot
                    # Calculate mid-price for portfolio valuation
                    bids = snapshot.get("bids", [])
                    asks = snapshot.get("asks", [])
                    if bids and asks:
                        mid_price = (bids[0]["price"] + asks[0]["price"]) / 2
                        current_prices[instrument.symbol_id] = mid_price
                    elif bids:
                        current_prices[instrument.symbol_id] = bids[0]["price"]
                    elif asks:
                        current_prices[instrument.symbol_id] = asks[0]["price"]
            
            # Update portfolio values and broadcast agent stats
            portfolio_tracker.update_portfolio_values(current_prices)
            await broadcast_agents_snapshot()
            
            # Broadcast to regular clients
            message = json.dumps({
                "type": "orderbooks",
                "data": snapshots
            })
            
            disconnected = set()
            for connection in regular_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.add(connection)
            regular_connections.difference_update(disconnected)
            
            # Broadcast to agents with portfolio updates
            for agent_id in agent_manager.get_all_agent_ids():
                agent = agent_manager.get_agent(agent_id)
                ws = agent_manager.get_websocket(agent_id)
                if agent and ws:
                    try:
                        # Send orderbooks
                        await ws.send_text(message)
                        
                        # Send portfolio update
                        portfolio_msg = json.dumps({
                            "type": "portfolio_update",
                            "cash": agent.cash,
                            "positions": {k: v.to_dict() for k, v in agent.positions.items()},
                            "total_value": agent.total_value,
                            "pnl": agent.pnl
                        })
                        await ws.send_text(portfolio_msg)
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    instruments = instrument_service.list_instruments()
    
    if not instruments:
        logger.info(
            "No instruments detected on startup. Adding default instrument %s",
            DEFAULT_BOOTSTRAP_INSTRUMENT["ticker"]
        )
        default_inst = instrument_service.add_instrument(
            DEFAULT_BOOTSTRAP_INSTRUMENT["ticker"],
            DEFAULT_BOOTSTRAP_INSTRUMENT["description"],
            DEFAULT_BOOTSTRAP_INSTRUMENT["industry"],
            DEFAULT_BOOTSTRAP_INSTRUMENT["initial_price"],
        )
        if default_inst:
            instruments = instrument_service.list_instruments()
            await broadcast_instruments_update()
        else:
            logger.error("Failed to create default instrument; system will remain without instruments.")
    
    asyncio.create_task(broadcast_orderbooks())
    asyncio.create_task(market_maker_service.bootstrap(instruments))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients and agents"""
    await websocket.accept()
    regular_connections.add(websocket)
    logger.info(f"Client connected. Total connections: {len(regular_connections)}")
    
    try:
        # Send initial data on connection
        instruments = instrument_service.list_instruments()
        
        # 1. Send instruments list
        await websocket.send_text(json.dumps({
            "type": "instruments",
            "data": [inst.to_dict() for inst in instruments]
        }))
        
        # 2. Send current orderbook snapshots for all instruments
        orderbook_snapshots = {}
        for instrument in instruments:
            snapshot = ob_client.get_snapshot(instrument.symbol_id)
            if snapshot["status"] == "success":
                orderbook_snapshots[instrument.symbol_id] = snapshot
        
        if orderbook_snapshots:
            await websocket.send_text(json.dumps({
                "type": "orderbooks",
                "data": orderbook_snapshots
            }))
        
        # 3. Send all news items (but not activity log)
        all_news = news_service.get_news()  # Get all news, no limit
        if all_news:
            await websocket.send_text(json.dumps({
                "type": "news_history",
                "data": [news.to_dict() for news in all_news]
            }))

        # Push agent snapshot so new dashboards have state
        await broadcast_agents_snapshot()
        
        # Listen for client messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from client: {e}, data: {data[:200]}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                continue
            
            if message.get("type") not in ["agent_register", "add_order", "cancel_order", "get_portfolio"]:
                logger.warning(f"Unknown message type: {message.get('type')}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}"
                }))
                continue
            
            if message["type"] == "agent_register":
                # Agent registration
                regular_connections.discard(websocket)
                agent_id = message.get("agent_id", str(uuid.uuid4()))
                name = message.get("name", f"Agent_{agent_id[:8]}")
                personality = message.get("personality", "neutral")
                starting_capital = message.get("starting_capital", 100000.0)
                
                agent = agent_manager.register_agent(agent_id, name, personality, starting_capital, websocket)
                
                await websocket.send_text(json.dumps({
                    "type": "agent_registered",
                    "agent_id": agent_id,
                    "agent": agent.to_dict()
                }))
                await broadcast_agents_snapshot()
                
                # Send current instruments
                await websocket.send_text(json.dumps({
                    "type": "instruments",
                    "data": [inst.to_dict() for inst in instruments]
                }))
                
                # Send current orderbook snapshots for all instruments (agents need this!)
                orderbook_snapshots = {}
                for instrument in instruments:
                    snapshot = ob_client.get_snapshot(instrument.symbol_id)
                    if snapshot["status"] == "success":
                        orderbook_snapshots[instrument.symbol_id] = snapshot
                
                if orderbook_snapshots:
                    await websocket.send_text(json.dumps({
                        "type": "orderbooks",
                        "data": orderbook_snapshots
                    }))
                    logger.debug(f"Sent initial orderbook snapshots to agent {name} ({len(orderbook_snapshots)} instruments)")
                
                # Send news history
                all_news = news_service.get_news()
                if all_news:
                    await websocket.send_text(json.dumps({
                        "type": "news_history",
                        "data": [news.to_dict() for news in all_news]
                    }))
            
            elif message["type"] == "add_order":
                # Place order with validation
                symbol_id = message.get("symbol_id", 1)
                side = message.get("side", "").upper()
                order_type = message.get("orderType", "LIMIT").upper()
                
                # Validate side
                if side not in ("BUY", "SELL"):
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid side: must be 'buy' or 'sell', got '{message.get('side')}'"}
                    }))
                    continue
                
                # Validate order type
                if order_type not in ("LIMIT", "MARKET"):
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid order type: must be 'LIMIT' or 'MARKET', got '{message.get('orderType')}'"}
                    }))
                    continue
                
                # Validate quantity
                quantity = message.get("quantity")
                try:
                    quantity = float(quantity)
                    if quantity <= 0 or not isinstance(quantity, (int, float)):
                        raise ValueError("Quantity must be a positive number")
                except (TypeError, ValueError) as e:
                    await websocket.send_text(json.dumps({
                        "type": "order_response",
                        "data": {"status": "error", "message": f"Invalid quantity: {e}"}
                    }))
                    continue
                
                # Validate price for LIMIT orders - THIS IS THE KEY FIX FOR PRICE 0 ISSUE
                price = message.get("price")
                if order_type == "LIMIT":
                    if price is None:
                        await websocket.send_text(json.dumps({
                            "type": "order_response",
                            "data": {"status": "error", "message": "Price is required for LIMIT orders"}
                        }))
                        continue
                    try:
                        price = float(price)
                        if price <= 0:
                            raise ValueError("Price must be positive for LIMIT orders")
                    except (TypeError, ValueError) as e:
                        await websocket.send_text(json.dumps({
                            "type": "order_response",
                            "data": {"status": "error", "message": f"Invalid price for LIMIT order: {e}"}
                        }))
                        continue
                else:
                    # MARKET orders don't need price, set to 0
                    price = 0
                
                agent_id = message.get("agent_id")
                
                result = ob_client.add_order(symbol_id, side, order_type, price, quantity)
                # Track performance metrics
                if result.get("status") == "success":
                    performance_metrics.record_order(quantity)
                elif "QUEUE_FULL" in str(result.get("message", "")):
                    performance_metrics.record_queue_full()
                
                if result["status"] == "success" and agent_id:
                    # Record trade if agent is placing order
                    agent = agent_manager.get_agent(agent_id)
                    instrument = instrument_service.get_instrument(symbol_id)
                    if agent:
                        # Note: In real system, we'd wait for trade execution event
                        # For now, we'll record it as a trade
                        try:
                            trade = portfolio_tracker.record_trade(
                                agent_id, symbol_id, side.lower(), price, int(quantity)
                            )
                            # Track trade in performance metrics
                            performance_metrics.record_trade(quantity)
                            await broadcast_agents_snapshot()
                        except (ValueError, TypeError, KeyError) as e:
                            logger.error(f"Error recording trade: {e}")
                        except Exception as e:
                            logger.exception(f"Unexpected error recording trade: {e}")
                    
                    # Broadcast order event to all regular clients (dashboard)
                    order_event = json.dumps({
                        "type": "order_placed",
                        "data": {
                            "agent_id": agent_id,
                            "agent_name": agent.name if agent else "Unknown",
                            "symbol_id": symbol_id,
                            "ticker": instrument.ticker if instrument else f"SYM{symbol_id}",
                            "side": side,
                            "order_type": order_type,
                            "price": price,
                            "quantity": quantity,
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                    
                    disconnected_clients = set()
                    for connection in regular_connections:
                        try:
                            await connection.send_text(order_event)
                        except:
                            disconnected_clients.add(connection)
                    regular_connections.difference_update(disconnected_clients)
                
                # Push fresh orderbook snapshot so dashboards/agents update in real-time
                await broadcast_orderbook_snapshots([symbol_id])
                
                await websocket.send_text(json.dumps({
                    "type": "order_response",
                    "data": result
                }))
            
            elif message["type"] == "cancel_order":
                symbol_id = message.get("symbol_id", 1)
                order_id = message["orderId"]
                result = ob_client.cancel_order(symbol_id, order_id)
                await websocket.send_text(json.dumps({
                    "type": "cancel_response",
                    "data": result
                }))
                
                if result.get("status") == "success":
                    await broadcast_orderbook_snapshots([symbol_id])
            
            elif message["type"] == "get_portfolio":
                agent_id = message.get("agent_id")
                if agent_id:
                    agent = agent_manager.get_agent(agent_id)
                    if agent:
                        await websocket.send_text(json.dumps({
                            "type": "portfolio_update",
                            "cash": agent.cash,
                            "positions": {k: v.to_dict() for k, v in agent.positions.items()},
                            "total_value": agent.total_value,
                            "pnl": agent.pnl
                        }))
            
    except WebSocketDisconnect:
        regular_connections.discard(websocket)
        agent_manager.unregister_websocket(websocket)
        logger.info(f"Client disconnected. Total connections: {len(regular_connections)}")
        await broadcast_agents_snapshot()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        regular_connections.discard(websocket)
        agent_manager.unregister_websocket(websocket)
        await broadcast_agents_snapshot()


# REST API Endpoints

@app.get("/api/instruments")
async def list_instruments():
    """List all instruments"""
    instruments = instrument_service.list_instruments()
    return [inst.to_dict() for inst in instruments]


@app.post("/api/instruments")
async def add_instrument(request: Request):
    """Add a new instrument"""
    data = await request.json()
    ticker = data.get("ticker")
    description = data.get("description", "")
    industry = data.get("industry", "")
    initial_price = data.get("initial_price")
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if initial_price is None:
        raise HTTPException(status_code=400, detail="initial_price is required")
    
    try:
        initial_price = float(initial_price)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="initial_price must be numeric")
    
    if initial_price <= 0:
        raise HTTPException(status_code=400, detail="initial_price must be positive")
    
    instrument = instrument_service.add_instrument(ticker, description, industry, initial_price)
    if instrument:
        await market_maker_service.ensure_instrument(instrument)
        await broadcast_instruments_update()
        return instrument.to_dict()
    raise HTTPException(status_code=500, detail="Failed to add instrument")


@app.delete("/api/instruments/{symbol_id}")
async def remove_instrument(symbol_id: int):
    """Remove an instrument"""
    success = instrument_service.remove_instrument(symbol_id)
    if success:
        await market_maker_service.remove_instrument(symbol_id)
        await broadcast_instruments_update()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Instrument not found")


@app.get("/api/agents")
async def list_agents():
    """List all agents with stats"""
    agents = agent_manager.list_agents()
    return [agent.to_dict() for agent in agents]


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    agent = agent_manager.get_agent(agent_id)
    if agent:
        return agent.to_dict()
    raise HTTPException(status_code=404, detail="Agent not found")


@app.get("/api/agents/{agent_id}/portfolio")
async def get_agent_portfolio(agent_id: str):
    """Get agent portfolio"""
    agent = agent_manager.get_agent(agent_id)
    if agent:
        return {
            "cash": agent.cash,
            "positions": {k: v.to_dict() for k, v in agent.positions.items()},
            "total_value": agent.total_value,
            "pnl": agent.pnl
        }
    raise HTTPException(status_code=404, detail="Agent not found")


@app.get("/api/agents/{agent_id}/trades")
async def get_agent_trades(agent_id: str, limit: Optional[int] = None):
    """Get agent trade history"""
    trades = portfolio_tracker.get_trades(agent_id, limit)
    return [trade.to_dict() for trade in trades]


@app.post("/api/news")
async def publish_news(request: Request):
    """Publish news. News is independent of instruments - agents interpret which instruments are affected."""
    data = await request.json()
    instrument_id = data.get("instrument_id")  # Optional
    content = data.get("content")
    impact_type = data.get("impact_type")
    
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    
    # Convert instrument_id to int if provided, None otherwise
    instrument_id = int(instrument_id) if instrument_id else None
    
    news = news_service.publish_news(content, instrument_id, impact_type)
    
    # Broadcast news to agents and dashboards
    await broadcast_news_update(news)
    
    return news.to_dict()


@app.get("/api/news")
async def get_news(limit: Optional[int] = None):
    """Get news history"""
    news_items = news_service.get_news(limit)
    return [news.to_dict() for news in news_items]


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Get leaderboard sorted by total asset value"""
    agents = agent_manager.list_agents()
    sorted_agents = sorted(agents, key=lambda a: a.total_value, reverse=True)
    return [agent.to_dict() for agent in sorted_agents]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "connections": len(regular_connections),
        "agents": len(agent_manager.get_all_agent_ids()),
        "instruments": len(instrument_service.list_instruments()),
        "backend": f"{CPP_HOST}:{CPP_PORT}"
    }


# Performance endpoint moved to router - keeping for backward compatibility if needed
# @app.get("/api/performance")
# async def get_performance_metrics():
#     """Get orderbook performance metrics."""
#     return performance_metrics.get_stats()


if __name__ == "__main__":
    logger.info("Starting OrderBook WebSocket Server...")
    logger.info(f"Backend: {CPP_HOST}:{CPP_PORT}")
    logger.info("WebSocket Server: ws://localhost:8000/ws")
    logger.info("REST API: http://localhost:8000/api")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
