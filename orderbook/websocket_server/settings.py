"""Application settings and environment configuration."""

from dataclasses import dataclass, field
import os


def _get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _get_env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass
class InstrumentDefaults:
    ticker: str = field(default_factory=lambda: _get_env("DEFAULT_INSTRUMENT_TICKER", "AAPL"))
    description: str = field(default_factory=lambda: _get_env("DEFAULT_INSTRUMENT_DESC", "Apple Inc."))
    industry: str = field(default_factory=lambda: _get_env("DEFAULT_INSTRUMENT_INDUSTRY", "Technology"))
    initial_price: float = field(default_factory=lambda: _get_env_float("DEFAULT_INSTRUMENT_PRICE", 150.0))


@dataclass
class Settings:
    cpp_host: str = field(default_factory=lambda: _get_env("CPP_HOST", "localhost"))
    cpp_port: int = field(default_factory=lambda: _get_env_int("CPP_PORT", 9999))
    broadcast_interval_seconds: float = field(
        default_factory=lambda: _get_env_float("BROADCAST_INTERVAL", 5.0)
    )
    default_instrument: InstrumentDefaults = field(default_factory=InstrumentDefaults)


settings = Settings()

