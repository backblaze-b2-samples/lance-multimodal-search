from fastapi import APIRouter, HTTPException

from app.service.dashboard import recent_searches
from app.types import RecentSearch

router = APIRouter()


@router.get("/dashboard/recent-searches", response_model=list[RecentSearch])
async def recent_searches_endpoint(limit: int = 20):
    """Recent search events for the dashboard table."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
    return recent_searches(limit=limit)
