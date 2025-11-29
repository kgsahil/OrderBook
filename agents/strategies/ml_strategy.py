"""ML-based trading strategy using scikit-learn."""

import logging
import numpy as np
from typing import Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os

from .base_strategy import BaseStrategy, MarketContext, TradingDecision

logger = logging.getLogger(__name__)


class MLStrategy(BaseStrategy):
    """
    Lightweight ML-based trading strategy using RandomForest.
    Uses scikit-learn for fast, lightweight predictions.
    """
    
    def __init__(self, personality: str, model_path: Optional[str] = None):
        super().__init__(personality)
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = model_path or os.getenv("ML_MODEL_PATH", "/tmp/trading_model.pkl")
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize or load the ML model."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model, self.scaler = pickle.load(f)
                logger.info(f"Loaded ML model from {self.model_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load model: {e}, creating new one")
        
        # Create new model
        self.model = RandomForestClassifier(
            n_estimators=50,  # Lightweight - only 50 trees
            max_depth=5,      # Shallow trees for speed
            random_state=42,
            n_jobs=1
        )
        
        # Train on synthetic data (in production, would use historical data)
        self._train_synthetic_model()
        logger.info("Initialized new ML model")
    
    def _train_synthetic_model(self):
        """Train model on synthetic trading patterns."""
        # Generate synthetic training data based on common trading patterns
        n_samples = 1000
        X = []
        y = []
        
        for _ in range(n_samples):
            # Features: spread_pct, price_change, position_qty, cash_ratio, news
            spread_pct = np.random.uniform(0, 0.05)
            price_change = np.random.uniform(-0.1, 0.1)
            position_qty = np.random.choice([-10, -5, 0, 5, 10])
            cash_ratio = np.random.uniform(0.1, 2.0)
            has_news = np.random.choice([0, 1])
            orderbook_depth = np.random.uniform(1, 10)
            
            features = [
                spread_pct,
                price_change,
                position_qty / 10.0,  # Normalize
                cash_ratio,
                has_news,
                orderbook_depth / 10.0
            ]
            X.append(features)
            
            # Label: BUY=0, SELL=1, HOLD=2
            # Simple rules for synthetic labels
            if spread_pct > 0.01 and price_change > 0.02 and cash_ratio > 0.5:
                label = 0  # BUY
            elif spread_pct > 0.01 and price_change < -0.02 and position_qty > 0:
                label = 1  # SELL
            elif has_news and cash_ratio > 0.3:
                label = 0  # BUY on news
            else:
                label = 2  # HOLD
            
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        # Fit scaler and model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        
        # Save model
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump((self.model, self.scaler), f)
        except Exception as e:
            logger.warning(f"Could not save model: {e}")
    
    def _extract_features(self, context: MarketContext) -> np.ndarray:
        """Extract features from market context."""
        orderbook_depth = (context.orderbook_depth.get("bids_count", 0) + 
                          context.orderbook_depth.get("asks_count", 0)) / 2.0
        
        features = np.array([[
            context.spread_pct,
            context.price_change,
            context.position_qty / 10.0,  # Normalize position
            context.cash / (context.mid_price * 10) if context.mid_price > 0 else 0,  # Cash ratio
            1.0 if context.has_recent_news else 0.0,
            orderbook_depth / 10.0
        ]])
        
        return self.scaler.transform(features)
    
    def decide(self, context: MarketContext) -> Optional[TradingDecision]:
        """Make trading decision using ML model."""
        try:
            features = self._extract_features(context)
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            
            # Get confidence
            confidence = max(probabilities)
            
            # Only act if confidence is reasonable (lowered for conservative)
            min_confidence = 0.3 if self.personality == "conservative" else 0.4
            if confidence < min_confidence:
                return None  # HOLD if uncertain
            
            action_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
            action = action_map.get(prediction, "HOLD")
            
            if action == "HOLD":
                return None
            
            # Calculate quantity and price based on personality and context
            if action == "BUY":
                if context.cash < context.mid_price * 2:
                    return None  # Not enough cash
                qty = min(10, int(context.cash / context.mid_price * 0.1))
                price = context.best_bid + context.spread * 0.1
                order_type = "LIMIT"
            else:  # SELL
                if context.position_qty <= 0 and not self.can_short(context):
                    return None  # Can't sell without position or short capability
                qty = min(abs(context.position_qty) if context.position_qty > 0 else 5, 10)
                price = context.best_ask - context.spread * 0.1
                order_type = "LIMIT"
            
            if qty <= 0:
                return None
            
            return TradingDecision(
                action=action,
                symbol_id=context.symbol_id,
                order_type=order_type,
                price=round(price, 2),
                quantity=qty,
                reasoning=f"ML prediction: {action} (confidence: {confidence:.2%})",
                score=confidence
            )
        
        except Exception as e:
            logger.error(f"ML strategy error: {e}")
            return None

