"""Service for managing agent connections and metadata."""

from typing import Dict, Optional, Set
from fastapi import WebSocket

from models.agent import Agent


class AgentManager:
    """Manages agent WebSocket connections and metadata."""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.connections: Dict[str, WebSocket] = {}
        self.agent_ids_by_ws: Dict[WebSocket, str] = {}
    
    def register_agent(self, agent_id: str, name: str, personality: str, 
                      starting_capital: float, websocket: WebSocket) -> Agent:
        """Register a new agent."""
        agent = Agent(
            agent_id=agent_id,
            name=name,
            personality=personality,
            cash=starting_capital,
            starting_capital=starting_capital
        )
        agent.total_value = starting_capital
        
        self.agents[agent_id] = agent
        self.connections[agent_id] = websocket
        self.agent_ids_by_ws[websocket] = agent_id
        
        return agent
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.connections:
            ws = self.connections[agent_id]
            self.agent_ids_by_ws.pop(ws, None)
            del self.connections[agent_id]
        self.agents.pop(agent_id, None)
    
    def unregister_websocket(self, websocket: WebSocket):
        """Unregister agent by WebSocket."""
        agent_id = self.agent_ids_by_ws.pop(websocket, None)
        if agent_id:
            self.unregister_agent(agent_id)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agent_by_websocket(self, websocket: WebSocket) -> Optional[Agent]:
        """Get agent by WebSocket."""
        agent_id = self.agent_ids_by_ws.get(websocket)
        if agent_id:
            return self.agents.get(agent_id)
        return None
    
    def get_websocket(self, agent_id: str) -> Optional[WebSocket]:
        """Get WebSocket for an agent."""
        return self.connections.get(agent_id)
    
    def list_agents(self) -> list[Agent]:
        """List all agents."""
        return list(self.agents.values())
    
    def get_all_agent_ids(self) -> Set[str]:
        """Get all agent IDs."""
        return set(self.agents.keys())
    
    def get_pending_agents(self) -> list[Agent]:
        """Get agents that don't have active WebSocket connections."""
        pending = []
        for agent_id, agent in self.agents.items():
            if agent_id not in self.connections:
                pending.append(agent)
        return pending
    
    def has_connection(self, agent_id: str) -> bool:
        """Check if an agent has an active WebSocket connection."""
        return agent_id in self.connections

