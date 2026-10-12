from typing import Literal

from fastapi import APIRouter, Query

from app.database import SessionDep
from app.models import OwnerAnalyticsSummary, OwnerComparison, RepositoryLeaderboardItem
from app.services.analytics import compare_owners, get_owner_summary, get_repository_leaderboard

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/owners/{owner_username}/summary", response_model=OwnerAnalyticsSummary)
async def read_owner_summary(owner_username: str, session: SessionDep) -> OwnerAnalyticsSummary:
    return get_owner_summary(owner_username, session)


@router.get("/repositories/leaderboard", response_model=list[RepositoryLeaderboardItem])
async def read_repository_leaderboard(
    session: SessionDep,
    metric: Literal["popularity", "stars", "forks"] = Query(default="popularity"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    owner_username: str | None = Query(default=None),
) -> list[RepositoryLeaderboardItem]:
    return get_repository_leaderboard(
        session,
        metric=metric,
        limit=limit,
        offset=offset,
        owner_username=owner_username,
    )


@router.get("/owners/compare", response_model=OwnerComparison)
async def read_owner_comparison(
    session: SessionDep,
    left: str = Query(...),
    right: str = Query(...),
) -> OwnerComparison:
    return compare_owners(left, right, session)
