"""Script to run trading agents with structured logging and error handling."""

import asyncio
import logging
import os
import sys
import signal
from typing import Optional

from agent_runner import AgentRunner
from config import load_config

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure logging for agents."""
    log_level = os.getenv("AGENT_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


class AgentManager:
    """Manages agent lifecycle and monitoring."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize agent manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "/app/config/agent_config.yaml"
        self.config = self._load_config()
        self.runner: Optional[AgentRunner] = None
        self._shutdown_event = asyncio.Event()
    
    def _load_config(self) -> dict:
        """Load configuration from file or defaults."""
        if os.path.exists(self.config_path):
            logger.info("Loading config from: %s", self.config_path)
            config = load_config(self.config_path)
        else:
            logger.warning("Config file not found: %s, using defaults", self.config_path)
            config = load_config(None)
        
        # Override with environment variables
        if "WS_URL" in os.environ:
            config["ws_url"] = os.environ["WS_URL"]
            logger.info("WS_URL overridden from environment: %s", config["ws_url"])
        
        return config
    
    async def start(self) -> None:
        """Start all agents."""
        max_retries = int(os.getenv("MAX_RETRIES", "5"))
        retry_delay = float(os.getenv("RETRY_DELAY", "5.0"))
        
        self.runner = AgentRunner(self.config)
        await self.runner.create_agents()
        
        try:
            await self.runner.start_all(max_retries=max_retries, retry_delay=retry_delay)
        except Exception as e:
            logger.exception("Failed to start agents: %s", e)
            raise
    
    async def stop(self) -> None:
        """Stop all agents gracefully."""
        if self.runner:
            await self.runner.stop_all()
        self._shutdown_event.set()
    
    async def monitor(self) -> None:
        """
        Monitor agents and handle failures.
        
        Exits if any agent fails to connect or encounters a fatal error.
        """
        if not self.runner:
            logger.error("No runner initialized")
            return
        
        while not self._shutdown_event.is_set():
            await asyncio.sleep(1)
            
            # Check if any agent task failed
            for i, task in enumerate(self.runner.tasks):
                if task.done():
                    try:
                        task.result()  # This will raise if task had an exception
                    except ConnectionError as e:
                        logger.error("Agent %d connection failed: %s", i + 1, e)
                        await self.stop()
                        sys.exit(1)
                    except Exception as e:
                        logger.exception("Agent %d error: %s", i + 1, e)
                        await self.stop()
                        sys.exit(1)
    
    async def run(self) -> None:
        """Main run loop."""
        try:
            await self.start()
            await self.monitor()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping agents...")
            await self.stop()
        except Exception as e:
            logger.exception("Fatal error: %s", e)
            await self.stop()
            sys.exit(1)


def _setup_signal_handlers(manager: AgentManager) -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info("Received signal %d, initiating shutdown...", signum)
        asyncio.create_task(manager.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    _setup_logging()
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    manager = AgentManager(config_path)
    
    # Setup signal handlers for graceful shutdown
    if sys.platform != "win32":  # Signal handlers don't work well on Windows
        _setup_signal_handlers(manager)
    
    try:
        await manager.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await manager.stop()
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        await manager.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

