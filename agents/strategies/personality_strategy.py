"""Personality-based strategy router."""

import logging
from typing import Optional

from .base_strategy import BaseStrategy, MarketContext, TradingDecision
from .heuristic_strategy import HeuristicStrategy
from .ml_strategy import MLStrategy

logger = logging.getLogger(__name__)


class PersonalityStrategy(BaseStrategy):
    """
    Routes to appropriate strategy based on personality.
    Combines ML and heuristic strategies based on agent personality.
    """
    
    def __init__(self, personality: str, use_ml: bool = True):
        super().__init__(personality)
        self.use_ml = use_ml
        
        # Initialize strategies
        self.heuristic_strategy = HeuristicStrategy(personality)
        if use_ml:
            try:
                self.ml_strategy = MLStrategy(personality)
            except Exception as e:
                logger.warning(f"ML strategy initialization failed: {e}, using heuristic only")
                self.ml_strategy = None
                self.use_ml = False
        else:
            self.ml_strategy = None
    
    def decide(self, context: MarketContext) -> Optional[TradingDecision]:
        """
        Decide using ML first, fallback to heuristic.
        Personality influences the decision weighting.
        """
        decisions = []
        
        # Try ML strategy first if available
        if self.use_ml and self.ml_strategy:
            try:
                ml_decision = self.ml_strategy.decide(context)
                if ml_decision:
                    # Adjust based on personality
                    ml_weight = self._get_personality_weight()
                    original_score = ml_decision.score
                    ml_decision.score *= ml_weight
                    logger.debug(f"ML decision: {ml_decision.action} (confidence: {original_score:.2%}, weighted: {ml_decision.score:.3f}, weight: {ml_weight})")
                    decisions.append(ml_decision)
                else:
                    logger.debug(f"ML returned None (low confidence or HOLD)")
            except Exception as e:
                logger.debug(f"ML decision failed: {e}")
        
        # Always try heuristic as fallback
        try:
            heuristic_decision = self.heuristic_strategy.decide(context)
            if heuristic_decision:
                # Heuristic gets base weight, adjusted by personality
                ml_weight = self._get_personality_weight()
                original_score = heuristic_decision.score
                heuristic_decision.score *= (1.0 - ml_weight * 0.5)
                logger.debug(f"Heuristic decision: {heuristic_decision.action} (score: {original_score:.3f}, weighted: {heuristic_decision.score:.3f})")
                decisions.append(heuristic_decision)
        except Exception as e:
            logger.debug(f"Heuristic decision failed: {e}")
        
        # Choose best decision
        if not decisions:
            return None
        
        # Select decision with highest score
        best_decision = max(decisions, key=lambda d: d.score)
        decision_type = "ML" if any(d.reasoning.startswith("ML prediction") for d in decisions if d == best_decision) else "Heuristic"
        logger.debug(f"Selected {decision_type} decision: {best_decision.action} (score: {best_decision.score:.3f})")
        
        # Personality-based filtering
        if self._should_filter_decision(best_decision, context):
            return None
        
        return best_decision
    
    def _get_personality_weight(self) -> float:
        """Get weight for ML vs heuristic based on personality."""
        weights = {
            "conservative": 0.3,  # Prefer heuristic (safer)
            "aggressive": 0.7,     # Prefer ML (more dynamic)
            "news_trader": 0.5,   # Balanced
            "market_maker": 0.2,  # Prefer heuristic (spread-based)
            "momentum": 0.6,      # Prefer ML (trend-following)
            "neutral": 0.5,       # Balanced
            "short_seller": 0.4,  # Prefer heuristic (rule-based shorting)
            "whale": 0.3,         # Prefer heuristic (large trades, rule-based)
            "predator": 0.4       # Prefer heuristic (counter-trading, rule-based)
        }
        return weights.get(self.personality.lower(), 0.5)
    
    def _should_filter_decision(self, decision: TradingDecision, context: MarketContext) -> bool:
        """Filter decisions based on personality risk tolerance."""
        if self.personality == "conservative":
            # Conservative: trade on reasonable confidence (lowered threshold)
            if decision.score < 0.3:  # Reduced from 0.6 to 0.3
                return True
            # Conservative: avoid large positions
            if decision.quantity > 5:
                decision.quantity = min(decision.quantity, 5)
        
        elif self.personality == "aggressive":
            # Aggressive: trade more frequently
            if decision.score < 0.3:
                return True
            # Aggressive: can take larger positions (increased from 20 to 50)
            decision.quantity = min(decision.quantity, 50)
        
        elif self.personality == "market_maker":
            # Market maker: only trade on good spreads
            if context.spread_pct < 0.001:
                return True
        
        elif self.personality == "short_seller":
            # Short seller: trade on reasonable opportunities
            if decision.score < 0.2:
                return True
            # Short seller: can take larger short positions
            if decision.action == "SELL" and decision.quantity > 0:
                decision.quantity = min(decision.quantity, 20)
        
        elif self.personality == "whale":
            # Whale: trade on very low thresholds to create volatility
            if decision.score < 0.05:
                return True
            # Whale: NO quantity cap - allow very large trades (50-200+ shares)
            # This is intentional to create large price movements
            # Just ensure minimum quantity
            if decision.quantity < 50:
                decision.quantity = max(decision.quantity, 50)  # Minimum 50 shares for whale
        
        elif self.personality == "predator":
            # Predator: trade on counter-opportunities (lower threshold)
            if decision.score < 0.15:
                return True
            # Predator: Medium-sized positions (30-80 shares) to counter whales
            # Not as large as whale, but substantial enough to matter
            
            decision.quantity = max(decision.quantity, 30)  # Minimum 30 shares
            decision.quantity = min(decision.quantity, 200)
        return False

