"""LLM-based trading agent using LangGraph."""

import asyncio
import hashlib
import json
import logging
import random
import time
from typing import Dict, Any, Optional, TypedDict, Tuple
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from agent_base import BaseAgent
from strategies import PersonalityStrategy
from strategies.base_strategy import MarketContext

logger = logging.getLogger(__name__)

DECISION_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
DECISION_CACHE_LOCK = asyncio.Lock()


class AgentState(TypedDict):
    """State for the agent decision graph."""
    orderbooks: Dict[int, Dict[str, Any]]
    portfolio: Optional[Dict[str, Any]]
    news: list
    instruments: list
    decision: Optional[str]
    action: Optional[Dict[str, Any]]


class LangGraphAgent(BaseAgent):
    """LLM-based trading agent using LangGraph for decision making."""
    
    def __init__(self, agent_id: str, name: str, personality: str,
                 ws_url: str = "ws://localhost:8000/ws",
                 starting_capital: float = 100000.0,
                 llm_provider: str = "gemini",
                 model: str = "gemini-2.0-flash-exp",
                 api_key: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, name, personality, ws_url, starting_capital)
        
        self.llm_provider = llm_provider
        self.model = model
        self.api_key = api_key
        self.config = config or {}
        self.enable_llm = self.config.get("enable_llm", False)  # Default: False (use fallback)
        self.min_price_change_pct = self.config.get("min_price_change_pct", 0.0025)
        self.decision_cache_ttl = self.config.get("decision_cache_ttl", 10.0)
        
        # Initialize LLM only if enabled
        self.llm = None
        if self.enable_llm:
            if llm_provider == "openai":
                if not api_key:
                    api_key = self._get_env_key("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("[%s] LLM enabled but OPENAI_API_KEY not set, falling back to heuristic strategy", self.name)
                    self.enable_llm = False
                else:
                    self.llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.7)
            elif llm_provider == "anthropic":
                if not api_key:
                    api_key = self._get_env_key("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("[%s] LLM enabled but ANTHROPIC_API_KEY not set, falling back to heuristic strategy", self.name)
                    self.enable_llm = False
                else:
                    self.llm = ChatAnthropic(model=model, api_key=api_key, temperature=0.7)
            elif llm_provider == "gemini" or llm_provider == "google":
                if not api_key:
                    api_key = self._get_env_key("GOOGLE_API_KEY")
                if not api_key:
                    logger.warning("[%s] LLM enabled but GOOGLE_API_KEY not set, falling back to heuristic strategy", self.name)
                    self.enable_llm = False
                else:
                    # Use gemini-2.0-flash-exp or gemini-1.5-flash based on availability
                    model_name = model if model else "gemini-2.0-flash-exp"
                    self.llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=api_key,
                        temperature=0.7
                    )
            else:
                logger.warning("[%s] Unknown LLM provider: %s, falling back to heuristic strategy", self.name, llm_provider)
                self.enable_llm = False
        
        if not self.enable_llm:
            logger.info("[%s] Using ML/heuristic fallback strategy (LLM disabled)", self.name)
        
        # Initialize strategy system (ML + heuristic based on personality)
        use_ml = self.config.get("use_ml_fallback", True)  # Use ML by default
        self.strategy = PersonalityStrategy(personality, use_ml=use_ml)
        
        # Build decision graph
        self.graph = self._build_graph()
        
        # Decision interval (minimum time between decisions)
        self.decision_interval = self.config.get("update_interval", 1.0)  # seconds
        self.running = False
        self.last_decision_time = 0.0
        self.pending_orderbook_update = False
        self.decision_lock = asyncio.Lock()
        self.last_mid_prices: Dict[int, float] = {}
        self.last_news_id: Optional[int] = None
        self.last_traded_instrument: Optional[int] = None  # Track last instrument traded
        self.pending_orders: Dict[int, Dict[str, Any]] = {}  # Track pending orders by symbol_id
    
    def _get_env_key(self, key: str) -> Optional[str]:
        """Get API key from environment."""
        import os
        return os.getenv(key)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph decision graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("observe", self._observe_orderbook)
        workflow.add_node("analyze", self._analyze_news)
        workflow.add_node("decide", self._decide_action)
        workflow.add_node("execute", self._execute_order)
        
        # Define edges
        workflow.set_entry_point("observe")
        workflow.add_edge("observe", "analyze")
        workflow.add_edge("analyze", "decide")
        workflow.add_conditional_edges(
            "decide",
            self._should_execute,
            {
                "execute": "execute",
                "end": END
            }
        )
        workflow.add_edge("execute", END)
        
        return workflow.compile()
    
    def _observe_orderbook(self, state: AgentState) -> AgentState:
        """Observe current orderbook state."""
        state["orderbooks"] = self.orderbooks.copy()
        state["instruments"] = self.instruments.copy()
        return state
    
    def _analyze_news(self, state: AgentState) -> AgentState:
        """Analyze recent news."""
        news = self.get_latest_news(5)
        state["news"] = news if news else []
        return state
    
    async def _decide_action(self, state: AgentState) -> AgentState:
        """Decide trading action using LLM (if enabled) or fallback heuristic strategy."""
        mid_prices = self._extract_mid_prices(state.get("orderbooks", {}))
        news_list = state.get("news", [])
        latest_news_id = news_list[-1].get("news_id") if news_list else None
        has_price_move = self._has_significant_move(mid_prices)
        has_news = latest_news_id is not None and latest_news_id != self.last_news_id
        
        # If LLM is disabled, use strategy system (ML + heuristic)
        if not self.enable_llm or self.llm is None:
            logger.debug("[%s] Using strategy system (ML/heuristic)", self.name)
            decision_dict = self._strategy_based_decision(state)
            state["action"] = decision_dict
            state["decision"] = decision_dict.get("reasoning", "Strategy-based decision")
            self.last_mid_prices = mid_prices
            self.last_news_id = latest_news_id
            self.last_decision_time = time.time()
            return state
        
        # For LLM: only proceed if there's a significant change
        if not has_price_move and not has_news:
            logger.debug("[%s] Skipping decision; no significant change", self.name)
            # Set default HOLD action to prevent None errors
            state["action"] = {"action": "HOLD", "reasoning": "No significant price move or news"}
            state["decision"] = "No significant change detected"
            self.last_mid_prices = mid_prices
            return state
        
        # LLM is enabled, try to use it
        context = self._build_context(state)
        cache_key = await self._make_cache_key(context)
        cached = await self._get_cached_decision(cache_key)
        if cached:
            logger.debug("[%s] Using cached LLM decision", self.name)
            cached_action = cached.get("action")
            # Ensure cached action is valid
            if cached_action is None or not isinstance(cached_action, dict):
                logger.warning("[%s] Cached action is invalid, using strategy", self.name)
                state["action"] = self._strategy_based_decision(state)
            else:
                state["action"] = cached_action
            state["decision"] = cached.get("decision", state["action"].get("reasoning", "Cached decision"))
            self.last_mid_prices = mid_prices
            self.last_news_id = latest_news_id
            self.last_decision_time = time.time()
            return state
        
        system_prompt = self._get_system_prompt()
        user_prompt = f"""Market: {context}

Decide: BUY/SELL/HOLD. Respond ONLY with JSON:
{{
    "action": "BUY|SELL|HOLD",
    "symbol_id": <id>,
    "order_type": "LIMIT|MARKET",
    "price": <price>,
    "quantity": <qty>,
    "reasoning": "<brief>"
}}"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                content = content[json_start:json_end]
            
            decision = json.loads(content)
            state["decision"] = decision.get("reasoning", "")
            state["action"] = decision
        except json.JSONDecodeError as e:
            logger.warning("[%s] JSON parse error: %s | content=%s", self.name, e, content[:200] if 'content' in locals() else 'N/A')
            logger.info("[%s] Falling back to strategy system due to LLM parse error", self.name)
            fallback_action = self._strategy_based_decision(state)
            state["action"] = fallback_action
            state["decision"] = fallback_action.get("reasoning", "LLM parse error, using strategy")
        except Exception as e:
            logger.exception("[%s] Decision error: %s", self.name, e)
            logger.info("[%s] Falling back to strategy system due to LLM error", self.name)
            fallback_action = self._strategy_based_decision(state)
            state["action"] = fallback_action
            state["decision"] = fallback_action.get("reasoning", "LLM error, using strategy")
        
        self.last_mid_prices = mid_prices
        self.last_news_id = latest_news_id
        self.last_decision_time = time.time()
        await self._store_cached_decision(cache_key, {"decision": state.get("decision"), "action": state.get("action")})
        return state
    
    def _should_execute(self, state: AgentState) -> str:
        """Determine if action should be executed."""
        action = state.get("action")
        
        # Handle None or non-dict actions
        if action is None:
            logger.warning("[%s] Action is None, defaulting to HOLD", self.name)
            return "end"
        
        if not isinstance(action, dict):
            logger.warning("[%s] Action is not a dict: %s, defaulting to HOLD", self.name, type(action))
            return "end"
        
        action_type = action.get("action", "HOLD")
        
        if action_type in ["BUY", "SELL"]:
            return "execute"
        return "end"
    
    async def _execute_order(self, state: AgentState) -> AgentState:
        """Execute the decided action."""
        action = state.get("action")
        
        # Handle None or non-dict actions
        if action is None or not isinstance(action, dict):
            logger.warning("[%s] Cannot execute: action is None or invalid", self.name)
            return state
        
        action_type = action.get("action", "HOLD")
        if action_type in ["BUY", "SELL"]:
            symbol_id = action.get("symbol_id")
            order_type = action.get("order_type", "LIMIT")
            price = action.get("price", 0)
            quantity = action.get("quantity", 0)
            
            # Validate price for LIMIT orders - CRITICAL: prevent price 0 orders
            if order_type.upper() == "LIMIT":
                if price is None or price <= 0:
                    logger.warning(
                        "[%s] Invalid or missing price (%s) for LIMIT order, skipping. Action: %s",
                        self.name, price, action
                    )
                    return state  # Skip this action
            elif order_type.upper() == "MARKET":
                # MARKET orders should have price=0 or None
                price = 0
            
            if symbol_id and quantity > 0:
                side = "BUY" if action_type == "BUY" else "SELL"
                await self.place_order(symbol_id, side, order_type, price, quantity)
                logger.info(
                    "[%s] %s %s symbol=%s qty=%s price=%s",
                    self.name,
                    action_type,
                    order_type,
                    symbol_id,
                    quantity,
                    price,
                )
                
                # Clear pending order after placing (will be updated when we get order response)
                # For now, clear after a delay to prevent immediate duplicate
                symbol_id_int = int(symbol_id)
                if symbol_id_int in self.pending_orders:
                    # Keep it for a short time to prevent duplicates
                    pass
        
        return state
    
    def _build_context(self, state: AgentState) -> str:
        """Build context string for LLM."""
        context_parts = []
        
        # Portfolio info
        if self.portfolio:
            context_parts.append(f"Portfolio: Cash=${self.portfolio.get('cash', 0):.2f}, "
                                f"Total Value=${self.portfolio.get('total_value', 0):.2f}, "
                                f"P&L=${self.portfolio.get('pnl', 0):.2f}")
        
        # Orderbook info
        for symbol_id, ob in state.get("orderbooks", {}).items():
            bids = ob.get("bids", [])
            asks = ob.get("asks", [])
            if bids and asks:
                best_bid = bids[0]["price"]
                best_ask = asks[0]["price"]
                spread = best_ask - best_bid
                context_parts.append(f"Instrument {symbol_id}: Bid={best_bid}, Ask={best_ask}, Spread={spread:.2f}")
        
        # News
        news = state.get("news", [])
        if news:
            context_parts.append(f"Recent news: {len(news)} items")
            for item in news[-3:]:  # Last 3 news items
                context_parts.append(f"  - {item.get('content', '')[:100]}")
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt based on personality."""
        base_prompt = f"""You are {self.name}, a trading agent with a {self.personality} personality.
Your goal is to maximize profit through intelligent trading decisions.
You have access to real-time orderbook data, news, and your portfolio.
Make decisions based on market conditions, news, and your risk tolerance."""
        
        personality_prompts = {
            "conservative": "You are risk-averse. Prefer small positions, limit orders, and wait for clear opportunities.",
            "aggressive": "You are risk-seeking. Take larger positions, use market orders when needed, and act quickly.",
            "news_trader": "You react strongly to news. When news breaks, analyze its impact and trade accordingly.",
            "market_maker": "You provide liquidity. Place limit orders on both sides to capture spreads.",
            "momentum": "You follow trends. Buy when prices are rising, sell when falling.",
            "neutral": "You balance risk and reward. Make rational decisions based on available information."
        }
        
        personality_prompt = personality_prompts.get(self.personality.lower(), personality_prompts["neutral"])
        
        return f"{base_prompt}\n\n{personality_prompt}"
    
    async def _make_decision(self):
        """Make a trading decision (called reactively or periodically)."""
        async with self.decision_lock:
            current_time = time.time()
            
            # Throttle decisions to avoid too frequent LLM calls
            if current_time - self.last_decision_time < self.decision_interval:
                logger.debug("[%s] Decision throttled (interval: %.1fs)", self.name, self.decision_interval)
                return
            
            if not self.connected:
                logger.debug("[%s] Not connected, skipping decision", self.name)
                return
            
            if not self.orderbooks:
                logger.debug("[%s] No orderbook data available, skipping decision", self.name)
                return
            
            logger.debug("[%s] Making decision with %d orderbooks", self.name, len(self.orderbooks))
            
            # Clear old pending orders (older than 10 seconds)
            old_threshold = current_time - 10.0
            self.pending_orders = {
                sid: order for sid, order in self.pending_orders.items()
                if order.get("timestamp", 0) > old_threshold
            }
            
            self.last_decision_time = current_time
            
            try:
                # Run decision graph with current state
                initial_state: AgentState = {
                    "orderbooks": self.orderbooks.copy(),
                    "portfolio": self.portfolio.copy() if self.portfolio else None,
                    "news": self.get_latest_news(5),
                    "instruments": self.instruments.copy(),
                    "decision": None,
                    "action": None
                }
                
                final_state = await self.graph.ainvoke(initial_state)
                
                # Log the decision outcome
                action = final_state.get("action")
                if action:
                    action_type = action.get("action", "UNKNOWN")
                    if not (action_type == "HOLD" or action_type == "UNKNOWN"):
                        logger.info("[%s] Decision made: %s | symbol_id=%s | qty=%s | price=%s", 
                                self.name, action_type, 
                                action.get("symbol_id"), 
                                action.get("quantity"),
                                action.get("price"))
                
                else:
                    logger.debug("[%s] Decision resulted in no action (HOLD or None)", self.name)
                
            except Exception as e:
                logger.exception("[%s] Decision error: %s", self.name, e)
    
    async def start_trading(self, max_retries: int = 5, retry_delay: float = 5.0):
        """Start the trading loop with reactive decision making."""
        if not await self.connect(max_retries=max_retries, retry_delay=retry_delay):
            logger.error("[%s] Cannot connect to OrderBook. Terminating.", self.name)
            raise ConnectionError(f"Failed to connect to {self.ws_url} after {max_retries} attempts")
        
        self.running = True
        
        # Set up reactive callbacks
        async def on_orderbook_update(orderbooks):
            """React to orderbook updates immediately."""
            logger.debug("[%s] Orderbook update received: %d instruments", self.name, len(orderbooks))
            self.pending_orderbook_update = True
            # Trigger decision if enough time has passed
            await self._make_decision()
        
        async def on_news(news_data):
            """React to news immediately."""
            logger.info("[%s] News received: %s", self.name, news_data.get("title", "Unknown"))
            # News is important, make decision quickly
            await asyncio.sleep(0.1)  # Small delay to process news
            await self._make_decision()
        
        self.on_orderbook_update = on_orderbook_update
        self.on_news = on_news
        
        # Request initial portfolio
        await self.get_portfolio()
        
        # Start listening in background (this handles all WebSocket messages)
        listen_task = asyncio.create_task(self.listen())
        
        # Wait for initial data and make first decision
        logger.info("[%s] Waiting for initial orderbook data...", self.name)
        max_wait_seconds = 10  # Wait up to 10 seconds for initial data
        check_interval = 0.5  # Check every 0.5 seconds
        max_attempts = int(max_wait_seconds / check_interval)
        
        for attempt in range(max_attempts):
            await asyncio.sleep(check_interval)
            if self.orderbooks:
                logger.info("[%s] Initial orderbooks received (%d instruments), making first decision", 
                           self.name, len(self.orderbooks))
                await self._make_decision()
                break
            # Check if we have instruments but no orderbooks yet
            if self.instruments and not self.orderbooks:
                logger.debug("[%s] Have %d instruments but no orderbook data yet (attempt %d/%d)...", 
                           self.name, len(self.instruments), attempt + 1, max_attempts)
            elif not self.instruments:
                logger.debug("[%s] No instruments available yet (attempt %d/%d)...", 
                           self.name, attempt + 1, max_attempts)
            else:
                logger.debug("[%s] Still waiting for orderbook data (attempt %d/%d)...", 
                           self.name, attempt + 1, max_attempts)
        else:
            if self.instruments:
                logger.warning("[%s] No orderbook data received after %d seconds (but %d instruments exist). "
                             "This may indicate an issue with the orderbook service.", 
                             self.name, max_wait_seconds, len(self.instruments))
            else:
                logger.info("[%s] No instruments available yet. Agents will start trading once instruments are created.", 
                           self.name)
        
        # Fallback periodic decision loop (in case no updates arrive)
        logger.info("[%s] Starting trading loop (interval: %.2fs)", self.name, self.decision_interval)
        while self.running:
            try:
                await asyncio.sleep(self.decision_interval)
                
                if not self.connected:
                    logger.warning("[%s] Connection lost, stopping", self.name)
                    break
                
                # Make decision if we have data but haven't decided recently
                if self.orderbooks:
                    time_since_last = time.time() - self.last_decision_time
                    if time_since_last >= self.decision_interval:
                        logger.debug("[%s] Periodic decision check (%.1fs since last)", self.name, time_since_last)
                        await self._make_decision()
                    else:
                        logger.debug("[%s] Skipping periodic decision (%.1fs < %.1fs)", 
                                   self.name, time_since_last, self.decision_interval)
                else:
                    logger.debug("[%s] Waiting for orderbook data...", self.name)
                
            except Exception as e:
                logger.exception("[%s] Trading loop error: %s", self.name, e)
                await asyncio.sleep(1)
        
        await self.disconnect()
        listen_task.cancel()
    
    async def stop_trading(self):
        """Stop the trading loop."""
        self.running = False

    def _extract_mid_prices(self, orderbooks: Dict[int, Dict[str, Any]]) -> Dict[int, float]:
        mids: Dict[int, float] = {}
        for key, snapshot in orderbooks.items():
            bids = snapshot.get("bids") or []
            asks = snapshot.get("asks") or []
            mid = None
            if bids and asks:
                mid = (float(bids[0]["price"]) + float(asks[0]["price"])) / 2
            elif bids:
                mid = float(bids[0]["price"])
            elif asks:
                mid = float(asks[0]["price"])
            if mid is not None:
                mids[int(key)] = mid
        return mids

    def _has_significant_move(self, mid_prices: Dict[int, float]) -> bool:
        for symbol_id, price in mid_prices.items():
            last = self.last_mid_prices.get(symbol_id)
            if not last:
                return True
            change_pct = abs(price - last) / max(last, 1e-9)
            if change_pct >= self.min_price_change_pct:
                return True
        return False

    async def _make_cache_key(self, context: str) -> str:
        return hashlib.sha256(context.encode("utf-8")).hexdigest()

    async def _get_cached_decision(self, cache_key: str) -> Optional[Dict[str, Any]]:
        async with DECISION_CACHE_LOCK:
            entry = DECISION_CACHE.get(cache_key)
            if not entry:
                return None
            timestamp, payload = entry
            if time.time() - timestamp <= self.decision_cache_ttl:
                return payload
            DECISION_CACHE.pop(cache_key, None)
            return None

    async def _store_cached_decision(self, cache_key: str, payload: Dict[str, Any]):
        async with DECISION_CACHE_LOCK:
            DECISION_CACHE[cache_key] = (time.time(), payload)
    
    def _strategy_based_decision(self, state: AgentState) -> Dict[str, Any]:
        """
        Use strategy system (ML + heuristic) to make trading decisions.
        Supports both long and short positions.
        """
        orderbooks = state.get("orderbooks", {})
        portfolio = state.get("portfolio")
        news = state.get("news", [])
        
        if not orderbooks:
            return {"action": "HOLD", "reasoning": "No orderbook data available"}
        
        # Find best opportunity across instruments
        best_decision = None
        best_score = 0.0
        
        # Convert to list and shuffle to randomize order
        instrument_list = list(orderbooks.items())
        import random
        random.shuffle(instrument_list)
        
        for symbol_id, ob in instrument_list:
            symbol_id = int(symbol_id)
            
            # Skip if pending order exists
            if symbol_id in self.pending_orders:
                continue
            
            bids = ob.get("bids", [])
            asks = ob.get("asks", [])
            
            if not bids or not asks:
                continue
            
            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])
            
            # Validate prices are positive
            if best_bid <= 0 or best_ask <= 0:
                logger.warning(
                    "[%s] Invalid orderbook prices for symbol %s: bid=%s, ask=%s, skipping",
                    self.name, symbol_id, best_bid, best_ask
                )
                continue
            
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            spread_pct = spread / mid_price if mid_price > 0 else 0
            
            if spread <= 0 or mid_price <= 0:
                continue
            
            # Get position and cash
            position = None
            if portfolio and portfolio.get("positions"):
                position = portfolio["positions"].get(str(symbol_id))
            
            position_qty = position.get("quantity", 0) if position else 0
            # Default cash to starting capital if portfolio not yet initialized
            cash = portfolio.get("cash", self.starting_capital) if portfolio else self.starting_capital
            
            # Calculate price change
            price_change = 0.0
            if symbol_id in self.last_mid_prices:
                last_mid = self.last_mid_prices[symbol_id]
                price_change = (mid_price - last_mid) / last_mid if last_mid > 0 else 0
            
            # Check for recent news
            has_recent_news = len(news) > 0 and any(
                n.get("instrument_id") == symbol_id or n.get("instrument_id") is None 
                for n in news[-3:]
            )
            
            # Build market context
            # Note: best_bid and best_ask are already validated above, so mid_price should be valid
            context = MarketContext(
                symbol_id=symbol_id,
                best_bid=best_bid,
                best_ask=best_ask,
                mid_price=mid_price,
                spread=spread,
                spread_pct=spread_pct,
                price_change=price_change,
                position_qty=position_qty,
                cash=cash,
                has_recent_news=has_recent_news,
                orderbook_depth={
                    "bids_count": len(bids),
                    "asks_count": len(asks)
                }
            )
            
            # Use strategy system to make decision
            try:
                decision = self.strategy.decide(context)
                if decision:
                    logger.debug("[%s] Strategy returned decision: %s (score=%.3f) for symbol %s", 
                               self.name, decision.action, decision.score, symbol_id)
                    if decision.score > best_score:
                        best_score = decision.score
                        best_decision = decision
                else:
                    logger.debug("[%s] Strategy returned None (HOLD) for symbol %s", self.name, symbol_id)
            except Exception as e:
                logger.warning("[%s] Strategy decision error: %s", self.name, e)
        
        # Convert TradingDecision to dict format
        if best_decision:
            symbol_id = best_decision.symbol_id
            if symbol_id:
                # Track pending order
                self.pending_orders[symbol_id] = {
                    "price": best_decision.price,
                    "quantity": best_decision.quantity,
                    "timestamp": time.time()
                }
                self.last_traded_instrument = symbol_id
            
            logger.info("[%s] Strategy decision: %s %s @ %.2f (qty=%d) - %s", 
                       self.name, best_decision.action, symbol_id, 
                       best_decision.price, best_decision.quantity, best_decision.reasoning)
            return {
                "action": best_decision.action,
                "symbol_id": best_decision.symbol_id,
                "order_type": best_decision.order_type,
                "price": best_decision.price,
                "quantity": best_decision.quantity,
                "reasoning": best_decision.reasoning
            }
        
        logger.debug("[%s] Strategy: No suitable opportunity found (checked %d instruments)", 
                    self.name, len(instrument_list))
        return {"action": "HOLD", "reasoning": "Strategy: No suitable opportunity found"}

