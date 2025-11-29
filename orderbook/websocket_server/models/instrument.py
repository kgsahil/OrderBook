"""Instrument data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Instrument:
    """Represents a tradable instrument."""
    symbol_id: int
    ticker: str
    description: str
    industry: str
    initial_price: float
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol_id': self.symbol_id,
            'ticker': self.ticker,
            'description': self.description,
            'industry': self.industry,
            'initial_price': self.initial_price,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Instrument':
        """Create from dictionary."""
        return cls(
            symbol_id=data['symbol_id'],
            ticker=data['ticker'],
            description=data['description'],
            industry=data['industry'],
            initial_price=float(data.get('initial_price', 0.0)),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        )

