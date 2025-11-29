"""Manages multiple agent instances with improved structure."""

import asyncio
import json
import logging
import random
import uuid
from typing import List, Dict, Any, Optional
import httpx
import websockets

from langraph_agent import LangGraphAgent
from config import AgentConfiguration

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Manages and runs multiple trading agents.
    
    Agents are created with random personalities, which determine their
    trading strategy (via PersonalityStrategy). Each personality uses a
    different combination of ML and heuristic strategies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agent runner.
        
        Args:
            config: Configuration dictionary with agent settings
        """
        # Use AgentConfiguration as single source of truth
        # Merge provided config with defaults
        defaults = AgentConfiguration.get_defaults()
        merged_config = {**defaults, **config}
        
        # Create validated configuration object
        try:
            self.config = AgentConfiguration(**merged_config)
            self.config.validate()
        except Exception as e:
            raise ValueError(f"Invalid agent configuration: {e}")
        
        self.agents: List[LangGraphAgent] = []
        self.tasks: List[asyncio.Task] = []
        self.running = False
        self.ws_url = self.config.ws_url
        self.api_url = self.ws_url.replace("ws://", "http://").replace("wss://", "https://").replace("/ws", "")
        self.http_client = httpx.AsyncClient(timeout=5.0)
        self.managed_agent_ids: set = set()  # Track which agent IDs we're managing
        self.listener_ws = None  # WebSocket connection for listening to agent_created events
        self.listener_task = None  # Task for the listener
    
    async def create_agents(self) -> List[LangGraphAgent]:
        """
        Create agent instances based on configuration.
        
        Each agent is assigned a random personality from the configured list.
        The personality determines the trading strategy used.
        
        Also checks for agents created from UI and spawns them.
        
        Returns:
            List of created agent instances
        """
        if self.agents:
            logger.warning("Agents already created. Skipping creation.")
            return self.agents
        
        for i in range(self.config.count):
            agent = self._create_single_agent(i + 1)
            self.agents.append(agent)
        
        logger.info("Created %d agents from config", len(self.agents))
        
        # Also check for agents created from UI that need to be spawned
        try:
            await self._spawn_ui_created_agents()
        except Exception as e:
            logger.warning("Failed to spawn UI-created agents: %s", e)
        
        logger.info("Total agents after UI check: %d", len(self.agents))
        return self.agents
    
    async def _spawn_ui_created_agents(self):
        """Check for agents created from UI and spawn them."""
        try:
            response = await self.http_client.get(f"{self.api_url}/api/agents")
            if response.status_code == 200:
                agents_data = response.json()
                for agent_data in agents_data:
                    agent_id = agent_data.get("agent_id")
                    if agent_id and agent_id not in self.managed_agent_ids:
                        # Check if this agent has a connection (if not, we need to spawn it)
                        # We'll spawn it if it doesn't have a connection
                        logger.info("Found UI-created agent: %s (%s), spawning...", 
                                  agent_data.get("name"), agent_id)
                        agent = self._create_agent_from_data(agent_data)
                        self.agents.append(agent)
                        self.managed_agent_ids.add(agent_id)
        except Exception as e:
            logger.warning("Error checking for UI-created agents: %s", e)
    
    def _create_agent_from_data(self, agent_data: Dict[str, Any]) -> LangGraphAgent:
        """Create an agent instance from agent data (from UI or API)."""
        agent_id = agent_data["agent_id"]
        name = agent_data.get("name", f"Agent_{agent_id[:8]}")
        personality = agent_data.get("personality", "neutral")
        starting_capital = float(agent_data.get("starting_capital", 100000.0))
        
        # Use config defaults for other settings
        config_dict = self.config.to_dict()
        randomized_interval = round(
            random.uniform(
                self.config.update_interval * 0.7,
                self.config.update_interval * 1.3
            ),
            2
        )
        config_dict['update_interval'] = max(0.2, randomized_interval)
        
        agent = LangGraphAgent(
            agent_id=agent_id,  # Use the existing agent_id from UI
            name=name,
            personality=personality,
            ws_url=self.ws_url,
            starting_capital=starting_capital,
            llm_provider=self.config.llm_provider,
            model=self.config.model,
            api_key=self.config.api_key,
            config=config_dict
        )
        
        return agent
    
    def _create_single_agent(self, index: int) -> LangGraphAgent:
        """
        Create a single agent instance.
        
        Args:
            index: Agent index (1-based) for naming
            
        Returns:
            LangGraphAgent instance
        """
        agent_id = str(uuid.uuid4())
        name = f"Agent_{index}"
        
        # Random personality selection - this determines the strategy
        personality = random.choice(self.config.personalities)
        
        # Random starting capital within configured range
        starting_capital = round(
            random.uniform(self.config.starting_capital_min, self.config.starting_capital_max),
            2
        )
        
        # Randomize update interval per agent (±30% variation for faster trading)
        # This prevents all agents from making decisions at the same time
        base_interval = self.config.update_interval
        interval_variation = base_interval * 0.3  # ±30% (reduced from 50% for faster trading)
        randomized_interval = round(
            random.uniform(
                base_interval - interval_variation,
                base_interval + interval_variation
            ),
            2
        )
        # Ensure minimum interval of 0.2 seconds for local models
        randomized_interval = max(0.2, randomized_interval)
        
        # Create agent with full config
        # Convert AgentConfiguration to dict for LangGraphAgent
        config_dict = self.config.to_dict()
        # Override update_interval with randomized value
        config_dict['update_interval'] = randomized_interval
        
        agent = LangGraphAgent(
            agent_id=agent_id,
            name=name,
            personality=personality,
            ws_url=self.config.ws_url,
            starting_capital=starting_capital,
            llm_provider=self.config.llm_provider,
            model=self.config.model,
            api_key=self.config.api_key,
            config=config_dict
        )
        
        logger.info(
            "Created %s | personality=%s | capital=$%.2f | interval=%.2fs | LLM=%s | ML=%s",
            name,
            personality,
            starting_capital,
            randomized_interval,
            "enabled" if self.config.enable_llm else "disabled",
            "enabled" if self.config.use_ml_fallback else "disabled"
        )
        
        return agent
    
    async def start_all(self, max_retries: int = 5, retry_delay: float = 5.0) -> None:
        """
        Start all agents with randomized initialization delays.
        
        This prevents all agents from starting at the same time and making
        decisions simultaneously, leading to more natural trading behavior.
        
        Args:
            max_retries: Maximum connection retry attempts per agent
            retry_delay: Delay between retry attempts (seconds)
        """
        if self.running:
            logger.warning("Agents already running")
            return
        
        if not self.agents:
            logger.error("No agents created. Call create_agents() first.")
            return
        
        self.running = True
        
        # Randomize initialization delays (0-5 seconds per agent)
        # This staggers agent startup to prevent synchronized behavior
        max_startup_delay = 5.0
        
        async def start_agent_with_delay(agent: LangGraphAgent, delay: float):
            """Start an agent after a random delay."""
            if delay > 0:
                logger.debug("[%s] Starting in %.2fs...", agent.name, delay)
                await asyncio.sleep(delay)
            await agent.start_trading(max_retries=max_retries, retry_delay=retry_delay)
        
        # Use the same function for monitoring
        self._start_agent_with_delay = start_agent_with_delay
        
        for agent in self.agents:
            # Random delay between 0 and max_startup_delay seconds
            startup_delay = random.uniform(0.0, max_startup_delay)
            task = asyncio.create_task(
                start_agent_with_delay(agent, startup_delay)
            )
            self.tasks.append(task)
        
        logger.info(
            "Starting %d agents with randomized delays (0-%.1fs) and intervals",
            len(self.agents),
            max_startup_delay
        )
        
        # Start WebSocket listener for real-time agent_created events
        self.listener_task = asyncio.create_task(self._listen_for_agent_events())
    
    async def _listen_for_agent_events(self):
        """Listen for real-time agent_created events via WebSocket."""
        max_retries = 5
        retry_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                logger.info("Connecting to orderbook WebSocket for agent event notifications...")
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                    self.listener_ws = ws
                    logger.info("Connected to orderbook WebSocket for agent events")
                    
                    while self.running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                            data = json.loads(message)
                            
                            if data.get("type") == "agent_created":
                                agent_data = data.get("data", {})
                                agent_id = agent_data.get("agent_id")
                                
                                if agent_id and agent_id not in self.managed_agent_ids:
                                    logger.info("Received agent_created event for: %s (%s), spawning...", 
                                              agent_data.get("name"), agent_id)
                                    await self._spawn_agent_from_event(agent_data)
                        except asyncio.TimeoutError:
                            # Timeout is fine, just continue listening
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("WebSocket connection closed, reconnecting...")
                            break
                        except Exception as e:
                            logger.warning("Error processing agent event: %s", e)
                            
            except Exception as e:
                logger.warning("Failed to connect listener WebSocket (attempt %d/%d): %s", 
                             attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to establish listener WebSocket after %d attempts", max_retries)
        
        self.listener_ws = None
    
    async def _spawn_agent_from_event(self, agent_data: Dict[str, Any]):
        """Spawn an agent from a real-time agent_created event."""
        agent = self._create_agent_from_data(agent_data)
        self.agents.append(agent)
        self.managed_agent_ids.add(agent_data["agent_id"])
        
        # Start the agent immediately
        startup_delay = random.uniform(0.0, 2.0)
        task = asyncio.create_task(
            self._start_agent_with_delay(agent, startup_delay)
        )
        self.tasks.append(task)
        logger.info("Spawned and started agent: %s", agent.name)
    
    async def _start_agent_with_delay(self, agent: LangGraphAgent, delay: float):
        """Start an agent after a delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        await agent.start_trading(max_retries=5, retry_delay=5.0)
    
    async def stop_all(self) -> None:
        """Stop all agents gracefully."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping all agents...")
        
        # Cancel listener task
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        # Close listener WebSocket
        if self.listener_ws:
            try:
                await self.listener_ws.close()
            except Exception:
                pass
            self.listener_ws = None
        
        # Stop all agents
        stop_tasks = [agent.stop_trading() for agent in self.agents]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.tasks.clear()
        logger.info("All agents stopped")
    
    def get_agents(self) -> List[LangGraphAgent]:
        """
        Get all agent instances.
        
        Returns:
            Copy of agents list
        """
        return self.agents.copy()
    
    def get_agent_by_id(self, agent_id: str) -> Optional[LangGraphAgent]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None if not found
        """
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def get_agent_by_name(self, name: str) -> Optional[LangGraphAgent]:
        """
        Get agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance or None if not found
        """
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
