"""Simple observability helpers. If prometheus_client is available, expose counters.
Otherwise, fallback to incrementing in-memory counters logged periodically.
"""
import logging
try:
    from prometheus_client import Counter, generate_latest, CollectorRegistry
    PROM_AVAILABLE = True
except Exception:
    PROM_AVAILABLE = False

logger = logging.getLogger(__name__)
_counters = {}

def incr(metric_name: str, amount: int = 1):
    if PROM_AVAILABLE:
        # in a full app you would register counters in a module-level registry
        Counter(metric_name, 'auto').inc(amount)
    else:
        _counters[metric_name] = _counters.get(metric_name, 0) + amount
        logger.info(f"Metric {metric_name} -> {_counters[metric_name]}")
