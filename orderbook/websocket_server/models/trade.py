"""Trade data model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """Represents a trade execution."""
    trade_id: int
    agent_id: str
    instrument_id: int
    side: str  # "buy" or "sell"
    price: float
    quantity: int
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'trade_id': self.trade_id,
            'agent_id': self.agent_id,
            'instrument_id': self.instrument_id,
            'side': self.side,
            'price': self.price,
            'quantity': self.quantity,
            'timestamp': self.timestamp.isoformat()
        }

