#!/usr/bin/env python3
"""
Test script to verify agents are working correctly.
Tests connection, orderbook updates, decision making, and order placement.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any, Optional

import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class AgentTester:
    """Test agent functionality."""
    
    def __init__(self, ws_url: str = "ws://localhost:8000/ws"):
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self.orderbooks_received = False
        self.instruments_received = False
        self.portfolio_received = False
        self.orders_placed = 0
        self.test_results = {
            "connection": False,
            "registration": False,
            "orderbook_updates": False,
            "instruments": False,
            "portfolio": False,
            "decision_making": False,
            "order_placement": False
        }
    
    async def connect(self):
        """Connect to WebSocket server."""
        try:
            logger.info(f"Connecting to {self.ws_url}...")
            self.ws = await websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10)
            self.connected = True
            self.test_results["connection"] = True
            logger.info("✓ Connected successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False
    
    async def register_agent(self):
        """Register as a test agent."""
        try:
            await self.ws.send(json.dumps({
                "type": "agent_register",
                "agent_id": "test_agent_001",
                "name": "TestAgent",
                "personality": "aggressive",
                "starting_capital": 100000.0
            }))
            logger.info("✓ Agent registration sent")
            self.test_results["registration"] = True
            return True
        except Exception as e:
            logger.error(f"✗ Registration failed: {e}")
            return False
    
    async def listen_for_updates(self, timeout: float = 10.0):
        """Listen for WebSocket messages and verify data."""
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "instruments":
                        instruments = data.get("data", [])
                        if instruments:
                            logger.info(f"✓ Received {len(instruments)} instruments")
                            self.test_results["instruments"] = True
                            self.instruments_received = True
                    
                    elif msg_type == "orderbooks":
                        orderbooks = data.get("data", {})
                        if orderbooks:
                            logger.info(f"✓ Received orderbook updates for {len(orderbooks)} instruments")
                            self.test_results["orderbook_updates"] = True
                            self.orderbooks_received = True
                            
                            # Check if orderbooks have liquidity
                            for symbol_id, ob in orderbooks.items():
                                bids = ob.get("bids", [])
                                asks = ob.get("asks", [])
                                if bids and asks:
                                    logger.info(f"  Instrument {symbol_id}: {len(bids)} bids, {len(asks)} asks")
                    
                    elif msg_type == "portfolio_update":
                        logger.info("✓ Received portfolio update")
                        self.test_results["portfolio"] = True
                        self.portfolio_received = True
                    
                    elif msg_type == "agent_registered":
                        logger.info("✓ Agent registered successfully")
                        self.test_results["registration"] = True
                    
                    elif msg_type == "news":
                        logger.info("✓ Received news update")
                    
                    elif msg_type == "news_history":
                        news = data.get("data", [])
                        logger.info(f"✓ Received {len(news)} news items")
                
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Connection closed")
                    break
        
        except Exception as e:
            logger.error(f"Error listening: {e}")
    
    async def test_order_placement(self):
        """Test placing an order."""
        try:
            # Get first available instrument
            if not self.instruments_received:
                logger.warning("No instruments received, skipping order test")
                return False
            
            # Wait a bit for orderbook data
            await asyncio.sleep(1)
            
            # Try to place a test order (we'll cancel it immediately)
            test_order = {
                "type": "add_order",
                "symbol_id": 1,  # Assuming at least one instrument exists
                "side": "BUY",
                "orderType": "LIMIT",
                "price": 100.0,
                "quantity": 1,
                "agent_id": "test_agent_001"
            }
            
            await self.ws.send(json.dumps(test_order))
            logger.info("✓ Test order sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get("type") == "order_response":
                    result = data.get("data", {})
                    if result.get("status") == "success":
                        logger.info("✓ Order placed successfully")
                        self.test_results["order_placement"] = True
                        self.orders_placed += 1
                        
                        # Cancel the test order
                        order_id = result.get("orderId")
                        if order_id:
                            cancel_msg = {
                                "type": "cancel_order",
                                "symbol_id": 1,
                                "orderId": int(order_id)
                            }
                            await self.ws.send(json.dumps(cancel_msg))
                            logger.info("✓ Test order cancelled")
                        return True
                    else:
                        logger.warning(f"Order failed: {result.get('message')}")
            except asyncio.TimeoutError:
                logger.warning("No order response received")
            
            return False
        
        except Exception as e:
            logger.error(f"✗ Order placement test failed: {e}")
            return False
    
    async def run_tests(self):
        """Run all tests."""
        logger.info("=" * 60)
        logger.info("Starting Agent Tests")
        logger.info("=" * 60)
        
        # Test 1: Connection
        if not await self.connect():
            self.print_results()
            return False
        
        # Test 2: Registration
        if not await self.register_agent():
            self.print_results()
            return False
        
        # Test 3: Listen for updates (instruments, orderbooks, portfolio)
        logger.info("\nListening for updates (10 seconds)...")
        await self.listen_for_updates(timeout=10.0)
        
        # Test 4: Order placement
        if self.orderbooks_received:
            logger.info("\nTesting order placement...")
            await self.test_order_placement()
        else:
            logger.warning("Skipping order test - no orderbook data received")
        
        # Final check
        await asyncio.sleep(2)
        
        self.print_results()
        
        # Close connection
        if self.ws:
            await self.ws.close()
        
        return self.all_tests_passed()
    
    def all_tests_passed(self) -> bool:
        """Check if all critical tests passed."""
        critical_tests = [
            "connection",
            "registration",
            "orderbook_updates",
            "instruments"
        ]
        return all(self.test_results[test] for test in critical_tests)
    
    def print_results(self):
        """Print test results."""
        logger.info("\n" + "=" * 60)
        logger.info("Test Results")
        logger.info("=" * 60)
        
        for test_name, passed in self.test_results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{test_name:25s}: {status}")
        
        logger.info("=" * 60)
        
        if self.all_tests_passed():
            logger.info("✓ All critical tests passed!")
        else:
            logger.warning("✗ Some tests failed")
        
        logger.info(f"Orders placed: {self.orders_placed}")


async def test_real_agents():
    """Test if real agents are running and active."""
    logger.info("\n" + "=" * 60)
    logger.info("Checking Real Agents Status")
    logger.info("=" * 60)
    
    try:
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not available, skipping real agents check")
            return False
        
        # Check agents via REST API
        api_url = "http://localhost:8000/api/agents"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(api_url)
                if response.status_code == 200:
                    agents = response.json()
                    logger.info(f"✓ Found {len(agents)} agents")
                    
                    for agent in agents:
                        name = agent.get("name", "Unknown")
                        total_value = agent.get("total_value", 0)
                        pnl = agent.get("pnl", 0)
                        positions = agent.get("positions", {})
                        logger.info(f"  {name}: Value=${total_value:.2f}, P&L=${pnl:.2f}, Positions={len(positions)}")
                    
                    return len(agents) > 0
                else:
                    logger.warning(f"API returned status {response.status_code}")
                    return False
        except httpx.RequestError as e:
            logger.warning(f"Could not connect to API: {e}")
            return False
    except Exception as e:
        logger.error(f"Error checking real agents: {e}")
        return False


async def main():
    """Main test function."""
    ws_url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws"
    
    tester = AgentTester(ws_url)
    success = await tester.run_tests()
    
    # Also check real agents if available
    await test_real_agents()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

