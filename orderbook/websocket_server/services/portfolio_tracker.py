"""Service for tracking agent portfolios and P&L."""

from typing import Dict, List, Optional
from datetime import datetime

from models.agent import Agent, Position
from models.trade import Trade


class PortfolioTracker:
    """Tracks agent portfolios, calculates P&L, and maintains trade history."""
    
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.trades: Dict[str, List[Trade]] = {}  # agent_id -> list of trades
        self.next_trade_id = 1
    
    def record_trade(self, agent_id: str, instrument_id: int, side: str, 
                    price: float, quantity: int) -> Trade:
        """Record a trade and update agent portfolio."""
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Create trade record
        trade = Trade(
            trade_id=self.next_trade_id,
            agent_id=agent_id,
            instrument_id=instrument_id,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=datetime.now()
        )
        self.next_trade_id += 1
        
        # Add to trade history
        if agent_id not in self.trades:
            self.trades[agent_id] = []
        self.trades[agent_id].append(trade)
        
        # Update agent portfolio
        if side == "buy":
            # Buying: reduce cash, increase position
            cost = price * quantity
            agent.cash -= cost
            agent.update_position(instrument_id, quantity, price)
        else:  # sell
            # Selling: increase cash, decrease position
            revenue = price * quantity
            agent.cash += revenue
            agent.update_position(instrument_id, -quantity, price)
        
        return trade
    
    def calculate_portfolio_value(self, agent_id: str, 
                                  current_prices: Dict[int, float]) -> float:
        """Calculate total portfolio value (cash + positions)."""
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            return 0.0
        
        total = agent.cash
        
        for instrument_id, position in agent.positions.items():
            current_price = current_prices.get(instrument_id, position.avg_price)
            total += position.quantity * current_price
        
        return total
    
    def update_portfolio_values(self, current_prices: Dict[int, float]):
        """Update all agent portfolio values and P&L."""
        for agent_id in self.agent_manager.get_all_agent_ids():
            agent = self.agent_manager.get_agent(agent_id)
            if agent:
                total_value = self.calculate_portfolio_value(agent_id, current_prices)
                agent.total_value = total_value
                agent.pnl = total_value - agent.starting_capital
    
    def get_trades(self, agent_id: str, limit: Optional[int] = None) -> List[Trade]:
        """Get trade history for an agent."""
        trades = self.trades.get(agent_id, [])
        if limit:
            return trades[-limit:]
        return trades
    
    def get_all_trades(self) -> Dict[str, List[Trade]]:
        """Get all trades for all agents."""
        return self.trades.copy()

