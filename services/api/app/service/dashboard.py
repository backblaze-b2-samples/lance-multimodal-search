"""Dashboard service — recent-searches aggregation for the dashboard table."""

from app.repo import get_recent_searches
from app.types import RecentSearch


def recent_searches(limit: int = 20) -> list[RecentSearch]:
    """Return the most recent search events (newest first)."""
    return [RecentSearch(**r) for r in get_recent_searches(limit=limit)]
