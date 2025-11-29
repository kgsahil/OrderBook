"""Base agent class with WebSocket client connection."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List

import websockets


class BaseAgent:
    """
    Base class for trading agents with WebSocket connection.
    
    Provides core functionality for:
    - WebSocket connection management
    - Orderbook and portfolio updates
    - News handling
    - Order placement and cancellation
    """
    
    def __init__(self, agent_id: str, name: str, personality: str, 
                 ws_url: str = "ws://localhost:8000/ws",
                 starting_capital: float = 100000.0):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique agent identifier
            name: Agent display name
            personality: Trading personality (determines strategy)
            ws_url: WebSocket server URL
            starting_capital: Initial capital amount
        """
        self.agent_id = agent_id
        self.name = name
        self.personality = personality
        self.ws_url = ws_url
        self.starting_capital = starting_capital
        
        # Connection state
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        
        # Market data
        self.orderbooks: Dict[int, Dict[str, Any]] = {}
        self.portfolio: Optional[Dict[str, Any]] = None
        self.news: List[Dict[str, Any]] = []
        self.instruments: List[Dict[str, Any]] = []
        
        # Callbacks
        self.on_orderbook_update: Optional[Callable] = None
        self.on_news: Optional[Callable] = None
        self.on_portfolio_update: Optional[Callable] = None
        
        # Logger
        self.logger = logging.getLogger(f"agent.{self.name}")
    
    async def connect(self, max_retries: int = 5, retry_delay: float = 5.0):
        """Connect to WebSocket server with retry logic."""
        for attempt in range(max_retries):
            try:
                self.logger.info("Attempting connection (%d/%d)...", attempt + 1, max_retries)
                self.ws = await websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10)
                self.connected = True
                
                # Register as agent
                await self.ws.send(json.dumps({
                    "type": "agent_register",
                    "agent_id": self.agent_id,
                    "name": self.name,
                    "personality": self.personality,
                    "starting_capital": self.starting_capital
                }))
                
                self.logger.info("Connected and registered")
                return True
            except Exception as e:
                self.logger.warning("Connection attempt %d failed: %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    self.logger.info("Retrying in %ss...", retry_delay)
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error("Failed to connect after %d attempts", max_retries)
                    self.connected = False
                    return False
        
        return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.logger.info("Disconnected")
    
    async def listen(self):
        """Listen for messages from server."""
        if not self.ws:
            return
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Connection closed by server")
            self.connected = False
        except Exception as e:
            self.logger.exception("Listen error: %s", e)
            self.connected = False
    
    async def handle_message(self, data: Dict[str, Any]):
        """Handle incoming message."""
        msg_type = data.get("type")
        
        if msg_type == "orderbooks":
            # Update orderbooks
            orderbooks_data = data.get("data", {})
            self.logger.debug("Received orderbook update: %d instruments", len(orderbooks_data))
            for symbol_id, snapshot in orderbooks_data.items():
                self.orderbooks[int(symbol_id)] = snapshot
            if self.on_orderbook_update:
                await self.on_orderbook_update(self.orderbooks)
        
        elif msg_type == "portfolio_update":
            # Update portfolio
            self.portfolio = data
            if self.on_portfolio_update:
                await self.on_portfolio_update(self.portfolio)
        
        elif msg_type == "news":
            # Receive news
            news_data = data.get("data")
            if news_data:
                self.news.append(news_data)
                if self.on_news:
                    await self.on_news(news_data)
        
        elif msg_type == "instruments":
            # Update instruments list
            self.instruments = data.get("data", [])
        
        elif msg_type == "agent_registered":
            print(f"[{self.name}] Registration confirmed")
    
    async def place_order(self, symbol_id: int, side: str, order_type: str, 
                         price: float, quantity: int) -> Dict[str, Any]:
        """Place an order."""
        if not self.connected or not self.ws:
            return {"status": "error", "message": "Not connected"}
        
        message = {
            "type": "add_order",
            "symbol_id": symbol_id,
            "side": side,
            "orderType": order_type,
            "price": price,
            "quantity": quantity,
            "agent_id": self.agent_id
        }
        
        await self.ws.send(json.dumps(message))
        return {"status": "sent"}
    
    async def cancel_order(self, symbol_id: int, order_id: int):
        """Cancel an order."""
        if not self.connected or not self.ws:
            return {"status": "error", "message": "Not connected"}
        
        message = {
            "type": "cancel_order",
            "symbol_id": symbol_id,
            "orderId": order_id
        }
        
        await self.ws.send(json.dumps(message))
        return {"status": "sent"}
    
    async def get_portfolio(self):
        """Request portfolio update."""
        if not self.connected or not self.ws:
            return
        
        message = {
            "type": "get_portfolio",
            "agent_id": self.agent_id
        }
        
        await self.ws.send(json.dumps(message))
    
    def get_orderbook(self, symbol_id: int) -> Optional[Dict[str, Any]]:
        """Get current orderbook for an instrument."""
        return self.orderbooks.get(symbol_id)
    
    def get_latest_news(self, count: int = 5) -> list:
        """Get latest news items."""
        return self.news[-count:] if len(self.news) > count else self.news

