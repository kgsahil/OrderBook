"""Heuristic-based trading strategy with shorting support."""

import logging
import random
from typing import Optional

from .base_strategy import BaseStrategy, MarketContext, TradingDecision

logger = logging.getLogger(__name__)


class HeuristicStrategy(BaseStrategy):
    """
    Heuristic-based trading strategy.
    Uses simple rules: momentum, spread capture, mean reversion, shorting.
    """
    
    def decide(self, context: MarketContext) -> Optional[TradingDecision]:
        """Make trading decision based on heuristics."""
        # Calculate score for this opportunity
        score = self._calculate_opportunity_score(context)
        
        if score <= 0:
            return None  # No good opportunity
        
        # Determine action based on personality and context
        decision = self._make_personality_decision(context, score)
        
        return decision
    
    def _calculate_opportunity_score(self, context: MarketContext) -> float:
        """Calculate opportunity score for this market context."""
        score = 0.0
        
        # Base score for liquidity (always present if we have bids/asks)
        if context.spread_pct > 0:
            score += 0.15  # Increased base score
        
        # Spread opportunity
        if context.spread_pct > 0.001:
            score += context.spread_pct * 15  # Increased multiplier
        
        # Momentum opportunity
        if abs(context.price_change) > 0.005:
            score += abs(context.price_change) * 5
        
        # News opportunity
        if context.has_recent_news:
            score += 0.3
        
        return score
    
    def _make_personality_decision(self, context: MarketContext, base_score: float) -> Optional[TradingDecision]:
        """Make decision based on personality."""
        
        if self.personality == "conservative":
            return self._conservative_decision(context, base_score)
        elif self.personality == "aggressive":
            return self._aggressive_decision(context, base_score)
        elif self.personality == "news_trader":
            return self._news_trader_decision(context, base_score)
        elif self.personality == "market_maker":
            return self._market_maker_decision(context, base_score)
        elif self.personality == "momentum":
            return self._momentum_decision(context, base_score)
        elif self.personality == "short_seller":
            return self._short_seller_decision(context, base_score)
        elif self.personality == "whale":
            return self._whale_decision(context, base_score)
        elif self.personality == "predator":
            return self._predator_decision(context, base_score)
        else:  # neutral or unknown
            return self._neutral_decision(context, base_score)
    
    def _conservative_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Conservative: Value investor - buys on dips, holds long-term.
        Real-world behavior: Patient, buys undervalued, sells on significant gains (20%+).
        """
        if context.cash < context.mid_price * 1.5:
            return None
        
        # VALUE BUYING: Buy on significant dips (value investing)
        if context.position_qty == 0:
            # Buy when price drops 2%+ (bargain hunting)
            if context.price_change < -0.02:
                qty = min(8, int(context.cash / context.mid_price * 0.08))
                if qty > 0:
                    price_variation = random.uniform(0.0, context.spread * 0.1)
                    calculated_price = round(context.best_bid + price_variation, 2)
                    # Note: Orderbook will validate price > 0, but we validate here for fail-fast
                    if calculated_price > 0:
                        return TradingDecision(
                            action="BUY",
                            symbol_id=context.symbol_id,
                            order_type="LIMIT",
                            price=calculated_price,
                            quantity=qty,
                            reasoning=f"Conservative: Value buy on dip ({context.price_change:.2%})",
                            score=score * 1.3
                        )
            # Also buy on moderate dips (1%+) with good spread
            elif context.price_change < -0.01 and context.spread_pct > 0.0005:
                qty = min(5, int(context.cash / context.mid_price * 0.05))
                if qty > 0:
                    price_variation = random.uniform(0.0, context.spread * 0.1)
                    calculated_price = round(context.best_bid + price_variation, 2)
                    # Note: Orderbook will validate price > 0, but we validate here for fail-fast
                    if calculated_price > 0:
                        return TradingDecision(
                            action="BUY",
                            symbol_id=context.symbol_id,
                            order_type="LIMIT",
                            price=calculated_price,
                            quantity=qty,
                            reasoning=f"Conservative: Accumulate on dip ({context.price_change:.2%})",
                            score=score
                        )
        
        # PROFIT TAKING: Sell on significant gains (20%+ from entry)
        # Conservative investors hold long-term, only sell on big wins
        if context.position_qty > 0:
            # Sell on large gains (take profits)
            if context.price_change > 0.05:  # 5%+ gain
                qty = min(context.position_qty, 5)
                return TradingDecision(
                    action="SELL",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_ask - context.spread * 0.1, 2),
                    quantity=qty,
                    reasoning=f"Conservative: Take profit on gain ({context.price_change:.2%})",
                    score=score * 1.2
                )
            # Exit on severe drops (stop loss at -10%+)
            elif context.price_change < -0.10:
                qty = min(context.position_qty, 3)
            return TradingDecision(
                action="SELL",
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_ask - context.spread * 0.1, 2),
                quantity=qty,
                    reasoning=f"Conservative: Stop loss on severe drop ({context.price_change:.2%})",
                    score=score * 1.5
            )
        
        return None
    
    def _aggressive_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Aggressive: Day trader - quick entries/exits, momentum trading, can short.
        Real-world behavior: Trades frequently, uses market orders, cuts losses quickly, rides momentum.
        """
        # MOMENTUM BUYING: Buy on upward momentum
        if context.cash > context.mid_price * 1.2:
            # Strong momentum up - jump in quickly
            if context.price_change > 0.002:  # 0.2%+ up
                qty = min(30, int(context.cash / context.mid_price * 0.25))
                use_market = random.random() < 0.4  # 40% market orders (aggressive)
                price_variation = random.uniform(0.0, context.spread * 0.1)
                return TradingDecision(
                    action="BUY",
                    symbol_id=context.symbol_id,
                    order_type="MARKET" if use_market else "LIMIT",
                    price=0 if use_market else round(context.best_bid + price_variation, 2),
                    quantity=qty,
                    reasoning=f"Aggressive: Momentum buy ({context.price_change:.2%})",
                    score=score * 1.5
                )
            
            # Quick spread capture
            elif context.spread_pct > 0.0008 and score > 0.15:
                qty = min(20, int(context.cash / context.mid_price * 0.2))
                price_variation = random.uniform(0.0, context.spread * 0.15)
                return TradingDecision(
                    action="BUY",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_bid + price_variation, 2),
                    quantity=qty,
                    reasoning=f"Aggressive: Spread capture ({context.spread_pct:.3%})",
                    score=score
                )
        
        # QUICK EXIT: Sell on any reversal (day traders cut losses fast)
        if context.position_qty > 0:
            # Exit on any drop (cut losses quickly)
            if context.price_change < -0.003:  # 0.3%+ drop
                qty = min(context.position_qty, 20)
                use_market = random.random() < 0.5  # Market order to exit fast
                return TradingDecision(
                    action="SELL",
                    symbol_id=context.symbol_id,
                    order_type="MARKET" if use_market else "LIMIT",
                    price=0 if use_market else round(context.best_ask - context.spread * 0.1, 2),
                    quantity=qty,
                    reasoning=f"Aggressive: Quick exit on reversal ({context.price_change:.2%})",
                    score=score * 1.4
                )
            # Take profit on small gains (day traders take profits quickly)
            elif context.price_change > 0.01:  # 1%+ gain
                qty = min(context.position_qty, 15)
                return TradingDecision(
                    action="SELL",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_ask - context.spread * 0.05, 2),
                    quantity=qty,
                    reasoning=f"Aggressive: Take profit ({context.price_change:.2%})",
                    score=score * 1.3
                )
        
        # SHORTING: Short on downward momentum (aggressive day traders short)
        if self.can_short(context) and context.price_change < -0.002:  # 0.2%+ down
            qty = min(15, int(context.cash / context.mid_price * 0.15))
            if qty > 0:
                use_market = random.random() < 0.3
                price_variation = random.uniform(0.0, context.spread * 0.1)
                return TradingDecision(
                    action="SELL",  # Short
                    symbol_id=context.symbol_id,
                    order_type="MARKET" if use_market else "LIMIT",
                    price=0 if use_market else round(context.best_ask - price_variation, 2),
                    quantity=qty,
                    reasoning=f"Aggressive: Short on momentum down ({context.price_change:.2%})",
                    score=score * 1.3
                )
        
        return None
    
    def _news_trader_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        News trader: Event-driven - reacts to news events.
        Real-world behavior: Buys on positive news, sells on negative news, uses market orders for speed.
        """
        # REACT TO NEWS: News traders act quickly on news
        if context.has_recent_news and context.cash > context.mid_price * 1.5:
            # Buy on news (assuming positive news - in real system would analyze sentiment)
            # News traders use market orders to get in fast
            qty = min(18, int(context.cash / context.mid_price * 0.18))
            use_market = random.random() < 0.6  # 60% market orders (react quickly)
            if qty > 0:
                return TradingDecision(
                    action="BUY",
                    symbol_id=context.symbol_id,
                    order_type="MARKET" if use_market else "LIMIT",
                    price=0 if use_market else round(context.mid_price, 2),
                    quantity=qty,
                    reasoning="News trader: Reacting to news event",
                    score=score * 1.6  # High score for news reaction
                )
        
        # EXIT ON NEWS FADE: Sell when news momentum fades
        if context.position_qty > 0 and not context.has_recent_news:
            # If we bought on news but no recent news, consider exiting
            if context.price_change > 0.02:  # Price up 2%+ (news already priced in)
                qty = min(context.position_qty, 12)
                return TradingDecision(
                    action="SELL",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_ask - context.spread * 0.1, 2),
                    quantity=qty,
                    reasoning="News trader: Exit after news priced in",
                    score=score * 1.2
                )
        
        return None
    
    def _market_maker_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Market maker: Liquidity provider - places both bids and asks.
        Real-world behavior: Profits from spread, provides liquidity, neutral bias.
        """
        if context.spread_pct < 0.0005:
            return None  # Spread too tight, not profitable
        
        # MARKET MAKERS PROVIDE LIQUIDITY ON BOTH SIDES
        # They buy at bid and sell at ask to capture spread
        
        if context.cash > context.mid_price * 2:
            # Place bid (buy order) to provide liquidity
            if random.random() < 0.5:  # 50% chance to place bid
                qty = min(12, int(context.cash / context.mid_price * 0.12))
                price_variation = random.uniform(0.0, context.spread * 0.3)  # Inside spread
                return TradingDecision(
                    action="BUY",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_bid + price_variation, 2),
                    quantity=qty,
                    reasoning=f"Market maker: Place bid (spread {context.spread_pct:.3%})",
                    score=score
                )
        
        # Place ask (sell order) if we have position
        if context.position_qty > 0 and context.spread_pct > 0.0008:
            qty = min(context.position_qty, 10)
            price_variation = random.uniform(0.0, context.spread * 0.3)  # Inside spread
            return TradingDecision(
                action="SELL",
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_ask - price_variation, 2),
                quantity=qty,
                reasoning=f"Market maker: Place ask (spread {context.spread_pct:.3%})",
                score=score
            )
        
        return None
    
    def _momentum_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Momentum: Trend follower - buys on uptrends, sells/shorts on downtrends.
        Real-world behavior: "The trend is your friend" - follows price direction.
        """
        # FOLLOW UPTREND: Buy when price is rising
        if context.price_change > 0.001 and context.cash > context.mid_price * 1.3:  # 0.1%+ up
            qty = min(20, int(context.cash / context.mid_price * 0.2))
            price_variation = random.uniform(0.0, context.spread * 0.1)
            return TradingDecision(
                action="BUY",
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_bid + price_variation, 2),
                quantity=qty,
                reasoning=f"Momentum: Follow uptrend ({context.price_change:.2%})",
                score=score * 1.5  # High score for trend following
            )
        
        # EXIT ON TREND REVERSAL: Sell when uptrend breaks
        if context.position_qty > 0:
            # Exit if trend reverses (price starts dropping)
            if context.price_change < -0.002:  # Trend reversed
                qty = min(context.position_qty, 15)
                return TradingDecision(
                    action="SELL",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_ask - context.spread * 0.1, 2),
                    quantity=qty,
                    reasoning=f"Momentum: Exit on trend reversal ({context.price_change:.2%})",
                    score=score * 1.3
                )
        
        # SHORT ON DOWNTREND: Short when price is falling (momentum down)
        if self.can_short(context) and context.price_change < -0.002:  # 0.2%+ down
            qty = min(15, int(context.cash / context.mid_price * 0.15))
            price_variation = random.uniform(0.0, context.spread * 0.1)
            return TradingDecision(
                action="SELL",  # Short
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_ask - price_variation, 2),
                quantity=qty,
                reasoning=f"Momentum: Short on downtrend ({context.price_change:.2%})",
                score=score * 1.4  # High score for following downtrend
            )
        
        return None
    
    def _short_seller_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Short seller: Bearish trader - shorts overvalued stocks, creates downward pressure.
        Real-world behavior: Shorts on upticks (betting on reversal), covers on drops (profit taking).
        """
        # COVER SHORT POSITIONS: Manage existing shorts
        if context.position_qty < 0:  # Has short position
            # Cover on significant drop (take profit)
            if context.price_change < -0.01:  # Price dropped 1%+ (good profit)
                qty = min(abs(context.position_qty), 20)
                return TradingDecision(
                    action="BUY",  # Cover short
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_bid + context.spread * 0.1, 2),
                    quantity=qty,
                    reasoning=f"Short seller: Cover on profit ({context.price_change:.2%})",
                    score=score * 1.6  # High score to take profit
                )
            # Cover on price reversal (stop loss - short squeeze risk)
            elif context.price_change > 0.005:  # Price rising 0.5%+ (cut losses)
                qty = min(abs(context.position_qty), 15)
                return TradingDecision(
                    action="BUY",  # Cover short
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",
                    price=round(context.best_bid + context.spread * 0.15, 2),
                    quantity=qty,
                    reasoning=f"Short seller: Cover on reversal/stop loss ({context.price_change:.2%})",
                    score=score * 1.5  # High score to avoid squeeze
                )
        
        # SHORT ON UPTICKS: Short sellers bet on reversals (overvalued)
        # Real short sellers short when price goes up (betting it will come down)
        if self.can_short(context) and context.position_qty >= 0:
            # Short on price spikes (betting on reversal)
            if context.price_change > 0.003:  # Price up 0.3%+ (overvalued)
                qty = min(18, int(context.cash / context.mid_price * 0.18))
                if qty > 0:
                    price_variation = random.uniform(0.0, context.spread * 0.1)
                    return TradingDecision(
                        action="SELL",  # Short
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_ask - price_variation, 2),
                        quantity=qty,
                        reasoning=f"Short seller: Short on uptick (betting on reversal) ({context.price_change:.2%})",
                        score=score * 1.5  # High score for shorting overvalued
                    )
            
            # Short on momentum down (follow the downtrend)
            elif context.price_change < -0.002:  # Price dropping (momentum down)
                qty = min(15, int(context.cash / context.mid_price * 0.15))
                if qty > 0:
                    price_variation = random.uniform(0.0, context.spread * 0.1)
                    return TradingDecision(
                        action="SELL",  # Short
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_ask - price_variation, 2),
                        quantity=qty,
                        reasoning=f"Short seller: Short on momentum down ({context.price_change:.2%})",
                        score=score * 1.3
                    )
        
        return None
    
    def _whale_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Whale: Makes very large trades to create significant price movements.
        Uses market orders frequently to move prices immediately.
        """
        # Whale needs substantial cash to make big moves
        if context.cash < context.mid_price * 2:
            return None
        
        # WHALE BUY - Create upward price pressure
        if context.cash > context.mid_price * 1.5:
            # Buy on any positive momentum (very low threshold)
            if context.price_change > 0.0001 or context.spread_pct > 0.0003:
                # Use 30-50% of available cash for huge positions
                qty = min(200, int(context.cash / context.mid_price * random.uniform(0.3, 0.5)))
                # 80% chance of market order to move price immediately
                use_market = random.random() < 0.8
                price_variation = random.uniform(0.0, context.spread * 0.2)
                
                if qty > 0:
                    return TradingDecision(
                        action="BUY",
                        symbol_id=context.symbol_id,
                        order_type="MARKET" if use_market else "LIMIT",
                        price=0 if use_market else round(context.best_bid + price_variation, 2),
                        quantity=qty,
                        reasoning=f"Whale: Large buy to create upward movement ({qty} shares, {context.price_change:.2%})",
                        score=score * 2.0  # High score to ensure execution
                    )
        
        # WHALE SELL - Create downward price pressure
        if context.position_qty > 0:
            # Sell large positions on any negative movement
            if context.price_change < -0.0001 or context.spread_pct > 0.0003:
                qty = min(context.position_qty, 150)
                use_market = random.random() < 0.8
                
                if qty > 0:
                    return TradingDecision(
                        action="SELL",
                        symbol_id=context.symbol_id,
                        order_type="MARKET" if use_market else "LIMIT",
                        price=0 if use_market else round(context.best_ask - context.spread * 0.1, 2),
                        quantity=qty,
                        reasoning=f"Whale: Large sell to create downward movement ({qty} shares, {context.price_change:.2%})",
                        score=score * 2.0
                    )
        
        # WHALE SHORT - Aggressive shorting to drive prices down
        if self.can_short(context):
            # Short on any negative momentum or even neutral with good spread
            if context.price_change < 0.0001 or (context.spread_pct > 0.0005 and score > 0.05):
                # Use 25-40% of available cash for large short positions
                qty = min(150, int(context.cash / context.mid_price * random.uniform(0.25, 0.4)))
                use_market = random.random() < 0.75
                price_variation = random.uniform(0.0, context.spread * 0.15)
                
                if qty > 0:
                    return TradingDecision(
                        action="SELL",  # Short is represented as SELL
                        symbol_id=context.symbol_id,
                        order_type="MARKET" if use_market else "LIMIT",
                        price=0 if use_market else round(context.best_ask - price_variation, 2),
                        quantity=qty,
                        reasoning=f"Whale: Large short to drive price down ({qty} shares, {context.price_change:.2%})",
                        score=score * 1.8
                    )
        
        # Even if no clear signal, whale can make random large trades to create volatility
        if random.random() < 0.1:  # 10% chance of random large trade
            if context.cash > context.mid_price * 2:
                qty = min(100, int(context.cash / context.mid_price * 0.2))
                use_market = True  # Always market order for random whale trades
                
                if qty > 0:
                    action = "BUY" if random.random() < 0.6 else "SELL"
                    return TradingDecision(
                        action=action,
                        symbol_id=context.symbol_id,
                        order_type="MARKET",
                        price=0,
                        quantity=qty,
                        reasoning=f"Whale: Random large {action} to create volatility ({qty} shares)",
                        score=0.5  # Moderate score
                    )
        
        return None

    def _predator_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """
        Predator: Counters whale movements by taking opposite positions.
        Detects whale activity through large price movements and orderbook imbalances.
        Aims to profit from whale-induced volatility reversals.
        """
        # Predator needs cash to counter-trade
        if context.cash < context.mid_price * 1.5:
            return None
        
        # Detect whale activity indicators
        large_price_move = abs(context.price_change) > 0.002  # 0.2%+ move suggests whale
        orderbook_imbalance = abs(context.orderbook_depth.get("bids_count", 0) - 
                                  context.orderbook_depth.get("asks_count", 0)) > 10
        
        # STRATEGY 1: Counter whale buying (price spike up)
        # When price spikes up, predator shorts/sells to profit from reversal
        if context.price_change > 0.002:  # Strong upward move (whale buying)
            if self.can_short(context):
                # Short to counter whale's upward pressure
                # Use 20-35% of cash, but smaller than whale to avoid being crushed
                qty = min(80, int(context.cash / context.mid_price * random.uniform(0.2, 0.35)))
                # Use limit orders to get better entry (predator is patient)
                price_variation = random.uniform(0.0, context.spread * 0.15)
                
                if qty > 0:
                    return TradingDecision(
                        action="SELL",  # Short
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",  # Limit order for better price
                        price=round(context.best_ask - price_variation, 2),
                        quantity=qty,
                        reasoning=f"Predator: Counter-short on whale buying spike ({qty} shares, price up {context.price_change:.2%})",
                        score=score * 1.8  # High score to execute counter-trade
                    )
            # If can't short, sell existing position
            elif context.position_qty > 0:
                qty = min(context.position_qty, 60)
                if qty > 0:
                    return TradingDecision(
                        action="SELL",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_ask - context.spread * 0.1, 2),
                        quantity=qty,
                        reasoning=f"Predator: Exit position on whale buying spike ({qty} shares)",
                        score=score * 1.5
                    )
        
        # STRATEGY 2: Counter whale selling (price drop)
        # When price drops sharply, predator buys to profit from bounce
        elif context.price_change < -0.002:  # Strong downward move (whale selling)
            # Buy to counter whale's downward pressure
            qty = min(80, int(context.cash / context.mid_price * random.uniform(0.2, 0.35)))
            # Use limit orders below current price to get good entry
            price_variation = random.uniform(0.0, context.spread * 0.2)
            
            if qty > 0:
                return TradingDecision(
                    action="BUY",
                    symbol_id=context.symbol_id,
                    order_type="LIMIT",  # Limit order for better price
                    price=round(context.best_bid - price_variation, 2),  # Buy below current
                    quantity=qty,
                    reasoning=f"Predator: Counter-buy on whale selling drop ({qty} shares, price down {context.price_change:.2%})",
                    score=score * 1.8
                )
        
        # STRATEGY 3: Detect orderbook imbalance (whale building position)
        # Large imbalance suggests whale activity
        if orderbook_imbalance and large_price_move:
            bids_count = context.orderbook_depth.get("bids_count", 0)
            asks_count = context.orderbook_depth.get("asks_count", 0)
            
            # Many bids but few asks = whale buying, predator should short
            if bids_count > asks_count + 15 and context.price_change > 0.001:
                if self.can_short(context):
                    qty = min(70, int(context.cash / context.mid_price * 0.25))
                    if qty > 0:
                        return TradingDecision(
                            action="SELL",
                            symbol_id=context.symbol_id,
                            order_type="LIMIT",
                            price=round(context.best_ask - context.spread * 0.1, 2),
                            quantity=qty,
                            reasoning=f"Predator: Short on orderbook imbalance (bids:{bids_count} vs asks:{asks_count})",
                            score=score * 1.6
                        )
            
            # Many asks but few bids = whale selling, predator should buy
            elif asks_count > bids_count + 15 and context.price_change < -0.001:
                qty = min(70, int(context.cash / context.mid_price * 0.25))
                if qty > 0:
                    return TradingDecision(
                        action="BUY",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_bid + context.spread * 0.1, 2),
                        quantity=qty,
                        reasoning=f"Predator: Buy on orderbook imbalance (asks:{asks_count} vs bids:{bids_count})",
                        score=score * 1.6
                    )
        
        # STRATEGY 4: Quick profit taking - if we have position and price moved favorably
        if context.position_qty > 0:
            # If we're long and price spiked (whale buying), take profit
            if context.price_change > 0.003:
                qty = min(context.position_qty, 50)
                if qty > 0:
                    return TradingDecision(
                        action="SELL",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_ask - context.spread * 0.05, 2),
                        quantity=qty,
                        reasoning=f"Predator: Take profit on whale-induced spike ({qty} shares)",
                        score=score * 1.4
                    )
        
        # STRATEGY 5: Fade extreme moves (mean reversion)
        # If price moved too far too fast, bet on reversal
        if abs(context.price_change) > 0.005:  # Very large move
            if context.price_change > 0.005 and self.can_short(context):
                # Price spiked too much, short for reversal
                qty = min(60, int(context.cash / context.mid_price * 0.2))
                if qty > 0:
                    return TradingDecision(
                        action="SELL",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_ask - context.spread * 0.1, 2),
                        quantity=qty,
                        reasoning=f"Predator: Fade extreme upward move ({qty} shares, {context.price_change:.2%})",
                        score=score * 1.5
                    )
            elif context.price_change < -0.005:
                # Price dropped too much, buy for bounce
                qty = min(60, int(context.cash / context.mid_price * 0.2))
                if qty > 0:
                    return TradingDecision(
                        action="BUY",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_bid + context.spread * 0.1, 2),
                        quantity=qty,
                        reasoning=f"Predator: Fade extreme downward move ({qty} shares, {context.price_change:.2%})",
                        score=score * 1.5
                    )
        
        return None
    
    def _neutral_decision(self, context: MarketContext, score: float) -> Optional[TradingDecision]:
        """Neutral: balanced approach with more buying opportunities."""
        # Lower cash requirement to allow more trading
        if context.cash > context.mid_price * 2:
            # Buy on spread opportunities
            if context.spread_pct > 0.0005:  # Lower threshold
                qty = min(12, int(context.cash / context.mid_price * 0.12))
            price_variation = random.uniform(0.0, context.spread * 0.1)
            return TradingDecision(
                action="BUY",
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_bid + price_variation, 2),
                quantity=qty,
                reasoning=f"Neutral: Balanced trade (spread {context.spread_pct:.3%})",
                score=score
                )
            
            # Buy on price dips (value buying)
            if context.price_change < -0.005:  # Price dropped 0.5%+
                qty = min(10, int(context.cash / context.mid_price * 0.1))
                if qty > 0:
                    price_variation = random.uniform(0.0, context.spread * 0.15)
                    return TradingDecision(
                        action="BUY",
                        symbol_id=context.symbol_id,
                        order_type="LIMIT",
                        price=round(context.best_bid + price_variation, 2),
                        quantity=qty,
                        reasoning=f"Neutral: Value buy on dip ({context.price_change:.2%})",
                        score=score * 1.1
                    )
        
        # Can sell existing position on significant gains
        if context.position_qty > 0 and context.price_change > 0.01:  # 1%+ gain
            qty = min(context.position_qty, 8)
            return TradingDecision(
                action="SELL",
                symbol_id=context.symbol_id,
                order_type="LIMIT",
                price=round(context.best_ask - context.spread * 0.1, 2),
                quantity=qty,
                reasoning=f"Neutral: Take profit on gain ({context.price_change:.2%})",
                score=score * 1.1
            )
        
        return None

