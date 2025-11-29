"""Agent configuration management with validation - single source of truth."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class AgentConfiguration:
    """
    Validated agent configuration - single source of truth for defaults.
    
    All default values are defined here. YAML files and environment variables
    override these defaults.
    """
    count: int = 2
    starting_capital_min: float = 50000.0
    starting_capital_max: float = 150000.0
    ws_url: str = "ws://localhost:8000/ws"
    enable_llm: bool = False
    llm_provider: str = "gemini"
    model: str = "gemini-2.0-flash-exp"
    api_key: Optional[str] = None
    update_interval: float = 4.0
    min_price_change_pct: float = 0.0025
    decision_cache_ttl: float = 12.0
    use_ml_fallback: bool = True
    personalities: List[str] = field(default_factory=lambda: [
        "conservative",
        "aggressive",
        "news_trader",
        "market_maker",
        "momentum",
        "neutral"
    ])
    
    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """
        Get default configuration as dictionary.
        
        Returns:
            Dictionary with default values from the dataclass
        """
        default_instance = cls()
        return asdict(default_instance)
    
    def validate(self) -> None:
        """Validate configuration values."""
        if self.count < 1:
            raise ValueError("Agent count must be at least 1")
        if self.starting_capital_min < 0:
            raise ValueError("Starting capital minimum must be non-negative")
        if self.starting_capital_max < self.starting_capital_min:
            raise ValueError("Starting capital max must be >= min")
        if self.update_interval <= 0:
            raise ValueError("Update interval must be positive")
        if not self.personalities:
            raise ValueError("At least one personality must be specified")
        if self.enable_llm and not self.api_key:
            # Warning, not error - will fall back to strategy system
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)


def _load_from_yaml(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML file
        
    Returns:
        Configuration dictionary from YAML (under 'agents' key if present)
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Extract 'agents' section if present, otherwise use root
        return config.get("agents", config)
    except Exception as e:
        raise ValueError(f"Failed to load config file {config_path}: {e}")


def _apply_environment_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply environment variable overrides to configuration.
    
    Environment variables take precedence over file/config defaults.
    
    Args:
        config: Configuration dictionary to modify
        
    Returns:
        Modified configuration dictionary
    """
    # LLM settings
    if "ENABLE_LLM" in os.environ:
        config["enable_llm"] = os.getenv("ENABLE_LLM", "false").lower() in ("true", "1", "yes")
    
    if "USE_ML_FALLBACK" in os.environ:
        config["use_ml_fallback"] = os.getenv("USE_ML_FALLBACK", "true").lower() in ("true", "1", "yes")
    
    # LLM provider settings
    if "LLM_PROVIDER" in os.environ:
        config["llm_provider"] = os.getenv("LLM_PROVIDER", "gemini")
    
    if "LLM_MODEL" in os.environ:
        config["model"] = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
    
    # API keys (only if LLM is enabled)
    if config.get("enable_llm", False):
        if "GOOGLE_API_KEY" in os.environ:
            config["api_key"] = os.getenv("GOOGLE_API_KEY")
            config["llm_provider"] = "gemini"
        elif "OPENAI_API_KEY" in os.environ:
            config["api_key"] = os.getenv("OPENAI_API_KEY")
            config["llm_provider"] = "openai"
        elif "ANTHROPIC_API_KEY" in os.environ:
            config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
            config["llm_provider"] = "anthropic"
    
    # Agent count
    if "AGENT_COUNT" in os.environ:
        config["count"] = int(os.getenv("AGENT_COUNT", "2"))
    
    # Update interval
    if "UPDATE_INTERVAL" in os.environ:
        config["update_interval"] = float(os.getenv("UPDATE_INTERVAL", "4.0"))
    
    # Other settings
    if "MIN_PRICE_CHANGE_PCT" in os.environ:
        config["min_price_change_pct"] = float(os.getenv("MIN_PRICE_CHANGE_PCT", "0.0025"))
    
    if "DECISION_CACHE_TTL" in os.environ:
        config["decision_cache_ttl"] = float(os.getenv("DECISION_CACHE_TTL", "12.0"))
    
    if "WS_URL" in os.environ:
        config["ws_url"] = os.getenv("WS_URL")
    
    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load agent configuration from YAML file or use defaults.
    
    Configuration priority (highest to lowest):
    1. Environment variables
    2. YAML file values
    3. AgentConfiguration dataclass defaults
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary (validated)
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Start with defaults from dataclass (single source of truth)
    config = AgentConfiguration.get_defaults()
    
    # Override with YAML file if provided
    if config_path and Path(config_path).exists():
        yaml_config = _load_from_yaml(config_path)
        # Merge YAML config into defaults (YAML overrides defaults)
        config.update({k: v for k, v in yaml_config.items() if v is not None})
    
    # Apply environment variable overrides (highest priority)
    config = _apply_environment_overrides(config)
    
    # Create and validate configuration object
    try:
        agent_cfg = AgentConfiguration(**config)
        agent_cfg.validate()
    except TypeError as e:
        raise ValueError(f"Invalid configuration field: {e}")
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")
    
    # Return as dictionary for backward compatibility
    return agent_cfg.to_dict()


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration.
    
    This function is kept for backward compatibility but now uses
    AgentConfiguration as the single source of truth.
    
    Returns:
        Default configuration dictionary
    """
    return AgentConfiguration.get_defaults()
