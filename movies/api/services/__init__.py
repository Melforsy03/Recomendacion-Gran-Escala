"""Services package initialization"""
from services.metrics_consumer import (
    get_latest_summary,
    get_latest_topn,
    get_latest_genres,
    get_metrics_history,
    get_last_update,
    subscribe_to_metrics,
    unsubscribe_from_metrics,
    start_consumer,
    stop_consumer
)

__all__ = [
    'get_latest_summary',
    'get_latest_topn',
    'get_latest_genres',
    'get_metrics_history',
    'get_last_update',
    'subscribe_to_metrics',
    'unsubscribe_from_metrics',
    'start_consumer',
    'stop_consumer'
]
