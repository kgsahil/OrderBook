"""Base strategy interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MarketContext:
    """Market context for strategy decisions."""
    symbol_id: int
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_pct: float
    price_change: float
    position_qty: int
    cash: float
    has_recent_news: bool
    orderbook_depth: Dict[str, int]  # bids_count, asks_count


@dataclass
class TradingDecision:
    """Trading decision result."""
    action: str  # "BUY", "SELL", "HOLD"
    symbol_id: int
    order_type: str  # "LIMIT", "MARKET"
    price: float
    quantity: int
    reasoning: str
    score: float


class BaseStrategy(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, personality: str):
        self.personality = personality
    
    @abstractmethod
    def decide(self, context: MarketContext) -> Optional[TradingDecision]:
        """
        Make a trading decision based on market context.
        
        Returns:
            TradingDecision if action should be taken, None for HOLD
        """
        pass
    
    def can_short(self, context: MarketContext) -> bool:
        """Check if agent can short (has position to sell or cash for short)."""
        # Make shorting harder to reduce downward bias
        # Require more cash to short (2.5x instead of 1.5x)
        return context.cash > context.mid_price * 2.5

