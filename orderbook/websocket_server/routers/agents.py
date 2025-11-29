"""Agent REST endpoints."""

import uuid
from fastapi import APIRouter, HTTPException, Request

from models.agent import Agent
from state import agent_manager, portfolio_tracker

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("")
async def list_agents():
    agents = agent_manager.list_agents()
    return [agent.to_dict() for agent in agents]


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_manager.get_agent(agent_id)
    if agent:
        return agent.to_dict()
    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/{agent_id}/portfolio")
async def get_portfolio(agent_id: str):
    agent = agent_manager.get_agent(agent_id)
    if agent:
        return {
            "cash": agent.cash,
            "positions": {k: v.to_dict() for k, v in agent.positions.items()},
            "total_value": agent.total_value,
            "pnl": agent.pnl,
        }
    raise HTTPException(status_code=404, detail="Agent not found")


@router.get("/{agent_id}/trades")
async def get_trades(agent_id: str, limit: int | None = None):
    trades = portfolio_tracker.get_trades(agent_id, limit)
    return [trade.to_dict() for trade in trades]


@router.get("/leaderboard")
async def get_leaderboard():
    agents = agent_manager.list_agents()
    sorted_agents = sorted(agents, key=lambda a: a.total_value, reverse=True)
    return [agent.to_dict() for agent in sorted_agents]


@router.post("")
async def create_agent(request: Request):
    """Create a new agent (metadata only - agent must connect via WebSocket)"""
    data = await request.json()
    name = data.get("name")
    personality = data.get("personality")
    starting_capital = data.get("starting_capital", 100000.0)
    
    if not name or not personality:
        raise HTTPException(status_code=400, detail="name and personality are required")
    
    try:
        starting_capital = float(starting_capital)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="starting_capital must be numeric")
    
    agent_id = str(uuid.uuid4())
    
    # Create agent metadata (will be fully registered when agent connects)
    agent = Agent(
        agent_id=agent_id,
        name=name,
        personality=personality,
        cash=starting_capital,
        starting_capital=starting_capital
    )
    agent.total_value = starting_capital
    
    # Register in agent manager (agent will connect via WebSocket later)
    agent_manager.agents[agent_id] = agent
    
    # Import here to avoid circular dependency
    from broadcast import broadcast_agents_snapshot, broadcast_agent_created
    await broadcast_agents_snapshot()
    # Broadcast agent creation event for real-time agent spawning
    await broadcast_agent_created(agent.to_dict())
    
    return agent.to_dict()

