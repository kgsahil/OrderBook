# Trading Strategies Module

This module provides a refactored, modular strategy system for trading agents.

## Architecture

### Base Strategy (`base_strategy.py`)
- Abstract base class for all strategies
- Defines `MarketContext` and `TradingDecision` data structures
- Provides common functionality like shorting capability checks

### Heuristic Strategy (`heuristic_strategy.py`)
- Rule-based trading strategy
- Supports both long and short positions
- Personality-based decision making:
  - **Conservative**: Small positions, no shorting
  - **Aggressive**: Larger positions, can short on downtrends
  - **News Trader**: Reacts to news events
  - **Market Maker**: Provides liquidity
  - **Momentum**: Follows trends, can short
  - **Neutral**: Balanced approach

### ML Strategy (`ml_strategy.py`)
- Lightweight ML model using scikit-learn RandomForest
- 50 trees, max depth 5 for fast inference
- Trained on synthetic trading patterns
- Predicts BUY/SELL/HOLD with confidence scores
- Only acts when confidence > 40%

### Personality Strategy (`personality_strategy.py`)
- Combines ML and heuristic strategies
- Routes decisions based on personality:
  - Conservative: 30% ML, 70% heuristic
  - Aggressive: 70% ML, 30% heuristic
  - Others: 50/50 split
- Filters decisions based on personality risk tolerance

## Features

### Shorting Support
- Aggressive and Momentum personalities can short
- Shorting is represented as SELL orders when position_qty <= 0
- Requires sufficient cash (2x mid_price)

### Multi-Instrument Trading
- Strategies evaluate all available instruments
- Shuffles instrument order for diversification
- Tracks last traded instrument to encourage rotation

### Price Variation
- Adds random price variation to avoid all agents placing at same price
- Improves fill probability

## Usage

```python
from strategies import PersonalityStrategy

# Initialize strategy
strategy = PersonalityStrategy(personality="aggressive", use_ml=True)

# Create market context
context = MarketContext(
    symbol_id=1,
    best_bid=100.0,
    best_ask=100.5,
    mid_price=100.25,
    spread=0.5,
    spread_pct=0.005,
    price_change=0.01,
    position_qty=0,
    cash=100000.0,
    has_recent_news=False,
    orderbook_depth={"bids_count": 5, "asks_count": 5}
)

# Get decision
decision = strategy.decide(context)
if decision:
    print(f"Action: {decision.action}, Price: {decision.price}, Qty: {decision.quantity}")
```

## Configuration

Set `USE_ML_FALLBACK=true` (default) to enable ML model.
Set `USE_ML_FALLBACK=false` to use only heuristic strategy.

## Dependencies

- `scikit-learn==1.3.2` - ML model
- `numpy==1.24.3` - Numerical operations

