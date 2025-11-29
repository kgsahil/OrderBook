"""Simple market maker to seed liquidity for instruments."""

import asyncio
import logging
import os
import random
import time
from typing import Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class MarketMakerService:
    """Maintains synthetic liquidity for each instrument."""
    
    def __init__(self, ob_client, on_book_update: Optional[Callable[[List[int]], Awaitable[None]]] = None):
        self.ob_client = ob_client
        self.refresh_interval = float(os.getenv("MARKET_MAKER_REFRESH_INTERVAL", "2.0"))
        self.levels = int(os.getenv("MARKET_MAKER_LEVELS", "2"))
        self.base_spread = float(os.getenv("MARKET_MAKER_BASE_SPREAD", "1.0"))
        self.tick_size = float(os.getenv("MARKET_MAKER_TICK_SIZE", "0.5"))
        self.quantity = int(os.getenv("MARKET_MAKER_QUANTITY", "50"))
        self.volatility = float(os.getenv("MARKET_MAKER_PRICE_JITTER", "0.001"))
        self.pulse_interval = float(os.getenv("MARKET_MAKER_PULSE_INTERVAL", "20.0"))
        self.pulse_quantity_multiplier = float(os.getenv("MARKET_MAKER_PULSE_SIZE_MULT", "2.0"))
        self.pulse_spread_factor = float(os.getenv("MARKET_MAKER_PULSE_SPREAD_FACTOR", "0.5"))
        
        self._tasks: Dict[int, asyncio.Task] = {}
        self._active_orders: Dict[int, Dict[str, List[int]]] = {}
        self._last_pulse: Dict[int, float] = {}
        self._on_book_update = on_book_update
    
    def set_book_update_callback(self, callback: Optional[Callable[[List[int]], Awaitable[None]]]):
        """Register async callback to notify when liquidity updates."""
        self._on_book_update = callback
    
    async def bootstrap(self, instruments):
        """Ensure all existing instruments have liquidity loops."""
        for instrument in instruments:
            await self.ensure_instrument(instrument)
    
    async def ensure_instrument(self, instrument):
        """Start a market making loop for an instrument if not already running."""
        symbol_id = instrument.symbol_id
        if symbol_id in self._tasks:
            logger.debug("Market maker already running for instrument %s", symbol_id)
            return
        logger.info("Starting market maker for instrument %s (ticker: %s, initial_price: %.2f)", 
                   symbol_id, instrument.ticker, instrument.initial_price or 100.0)
        task = asyncio.create_task(self._run_for_instrument(symbol_id, instrument.initial_price or 100.0))
        self._tasks[symbol_id] = task
        self._active_orders[symbol_id] = {"buy": [], "sell": []}
        self._last_pulse[symbol_id] = time.time()
    
    async def remove_instrument(self, symbol_id: int):
        """Stop market making for an instrument."""
        task = self._tasks.pop(symbol_id, None)
        if task:
            task.cancel()
        await self._cancel_orders(symbol_id)
        self._active_orders.pop(symbol_id, None)
        self._last_pulse.pop(symbol_id, None)
    
    async def _run_for_instrument(self, symbol_id: int, reference_price: float):
        """Continuous loop to maintain liquidity."""
        price_hint = max(reference_price, 1.0)
        try:
            while True:
                snapshot = self.ob_client.get_snapshot(symbol_id)
                mid = self._get_mid_price(symbol_id)
                
                # Check if orderbook is empty or has low liquidity
                bids = snapshot.get("bids", []) if snapshot.get("status") == "success" else []
                asks = snapshot.get("asks", []) if snapshot.get("status") == "success" else []
                has_liquidity = len(bids) > 0 and len(asks) > 0
                
                if mid is None:
                    mid = price_hint * (1 + random.uniform(-self.volatility, self.volatility))
                price_hint = mid
                
                pulse = self._should_pulse(symbol_id)
                
                # If no liquidity, be more aggressive (shorter interval, more levels, larger quantity)
                if not has_liquidity:
                    # Use faster refresh when no liquidity
                    await self._refresh_orders(symbol_id, price_hint, pulse=True, aggressive=True)
                    if self._on_book_update:
                        await self._on_book_update([symbol_id])
                    await asyncio.sleep(self.refresh_interval * 0.5)  # 2x faster when no liquidity
                else:
                    await self._refresh_orders(symbol_id, price_hint, pulse)
                    if self._on_book_update:
                        await self._on_book_update([symbol_id])
                    await asyncio.sleep(self.refresh_interval)
        except asyncio.CancelledError:
            await self._cancel_orders(symbol_id)
    
    def _should_pulse(self, symbol_id: int) -> bool:
        last = self._last_pulse.get(symbol_id, 0)
        now = time.time()
        if now - last >= self.pulse_interval:
            self._last_pulse[symbol_id] = now
            return True
        return False
    
    async def _refresh_orders(self, symbol_id: int, mid_price: float, pulse: bool = False, aggressive: bool = False):
        """Cancel existing orders and place fresh ones around the current mid."""
        await self._cancel_orders(symbol_id)
        
        bids = []
        asks = []
        
        # When aggressive (no liquidity), use more levels, larger quantity, tighter spread
        if aggressive:
            levels = self.levels * 2  # Double the levels
            spread = self.base_spread * 0.5  # Tighter spread
            qty = int(self.quantity * 2)  # Double the quantity
            label = "AGGRESSIVE"
        elif pulse:
            spread = self.base_spread * self.pulse_spread_factor
            qty = int(self.quantity * self.pulse_quantity_multiplier)
            levels = self.levels
            label = "PULSE"
        else:
            spread = self.base_spread
            qty = self.quantity
            levels = self.levels
            label = "normal"
        
        for level in range(1, levels + 1):
            offset = spread + (level - 1) * self.tick_size
            bid_price = max(1.0, mid_price - offset)
            ask_price = max(bid_price + self.tick_size, mid_price + offset)
            
            bid_order = self.ob_client.add_order(symbol_id, "BUY", "LIMIT", bid_price, qty)
            if bid_order.get("status") == "success":
                order_id = int(bid_order.get("orderId", 0))
                bids.append(order_id)
                logger.debug("Market maker [%s] placed BUY order: %d @ %.2f qty=%d (%s)", 
                            symbol_id, order_id, bid_price, qty, label)
            else:
                logger.warning("Market maker [%s] failed to place BUY order @ %.2f: %s", 
                             symbol_id, bid_price, bid_order.get("message", "unknown error"))
            
            ask_order = self.ob_client.add_order(symbol_id, "SELL", "LIMIT", ask_price, qty)
            if ask_order.get("status") == "success":
                order_id = int(ask_order.get("orderId", 0))
                asks.append(order_id)
                logger.debug("Market maker [%s] placed SELL order: %d @ %.2f qty=%d (%s)", 
                            symbol_id, order_id, ask_price, qty, label)
            else:
                logger.warning("Market maker [%s] failed to place SELL order @ %.2f: %s", 
                             symbol_id, ask_price, ask_order.get("message", "unknown error"))
        
        self._active_orders[symbol_id] = {"buy": bids, "sell": asks}
        
        if aggressive or pulse:
            logger.info("Market maker [%s] %s: placed %d bids, %d asks @ mid=%.2f", 
                       symbol_id, label, len(bids), len(asks), mid_price)
        elif len(bids) > 0 or len(asks) > 0:
            logger.debug("Market maker [%s] refreshed: %d bids, %d asks @ mid=%.2f", 
                        symbol_id, len(bids), len(asks), mid_price)
    
    async def _cancel_orders(self, symbol_id: int):
        """Cancel any resting maker orders for an instrument."""
        orders = self._active_orders.get(symbol_id)
        if not orders:
            return
        for order_id in orders.get("buy", []):
            self.ob_client.cancel_order(symbol_id, order_id)
        for order_id in orders.get("sell", []):
            self.ob_client.cancel_order(symbol_id, order_id)
        self._active_orders[symbol_id] = {"buy": [], "sell": []}
    
    def _get_mid_price(self, symbol_id: int) -> Optional[float]:
        """Pull latest snapshot and compute mid price."""
        snapshot = self.ob_client.get_snapshot(symbol_id)
        if snapshot.get("status") != "success":
            return None
        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])
        if bids and asks:
            return (bids[0]["price"] + asks[0]["price"]) / 2
        if bids:
            return float(bids[0]["price"])
        if asks:
            return float(asks[0]["price"])
        return None

