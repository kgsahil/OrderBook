"""Agent data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Position:
    """Agent position in an instrument."""
    instrument_id: int
    quantity: int
    avg_price: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'instrument_id': self.instrument_id,
            'quantity': self.quantity,
            'avg_price': self.avg_price
        }


@dataclass
class Agent:
    """Represents a trading agent."""
    agent_id: str
    name: str
    personality: str
    cash: float
    positions: Dict[int, Position] = field(default_factory=dict)
    total_value: float = 0.0
    pnl: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    starting_capital: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'personality': self.personality,
            'cash': self.cash,
            'positions': {k: v.to_dict() for k, v in self.positions.items()},
            'total_value': self.total_value,
            'pnl': self.pnl,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'starting_capital': self.starting_capital
        }
    
    def get_position(self, instrument_id: int) -> Optional[Position]:
        """Get position for an instrument."""
        return self.positions.get(instrument_id)
    
    def update_position(self, instrument_id: int, quantity: int, price: float):
        """Update position after a trade."""
        if instrument_id in self.positions:
            pos = self.positions[instrument_id]
            total_cost = (pos.quantity * pos.avg_price) + (quantity * price)
            total_qty = pos.quantity + quantity
            if total_qty != 0:
                pos.avg_price = total_cost / total_qty
            pos.quantity = total_qty
            if pos.quantity == 0:
                del self.positions[instrument_id]
        else:
            if quantity != 0:
                self.positions[instrument_id] = Position(instrument_id, quantity, price)

