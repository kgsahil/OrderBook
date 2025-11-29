"""Performance metrics REST endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/performance", tags=["Performance"])

# Performance metrics will be injected via dependency or passed at router registration
# For now, we use a module-level variable that will be set by server.py
_performance_metrics = None


def set_performance_metrics(metrics):
    """Set the performance metrics instance."""
    global _performance_metrics
    _performance_metrics = metrics


@router.get("")
async def get_performance_metrics():
    """Get orderbook performance metrics."""
    if _performance_metrics is None:
        # Fallback: try to import from server (lazy import to avoid circular dependency)
        try:
            from server import performance_metrics
            return performance_metrics.get_stats()
        except ImportError:
            return {"error": "Performance metrics not available"}
    return _performance_metrics.get_stats()

