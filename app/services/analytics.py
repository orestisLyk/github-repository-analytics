from statistics import median

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select

from app.models import (
    Owner,
    OwnerAnalyticsSummary,
    OwnerComparison,
    Repository,
    RepositoryLeaderboardItem,
)

# Popularity is an engagement-oriented ranking metric that favors stars
# and gives forks additional weight as a signal of adoption.
POPULARITY_FORK_WEIGHT = 2

# Engagement score is a bounded heuristic (0-100) intended for relative
# comparison in this API, not a canonical GitHub health metric.
ENGAGEMENT_BASELINE = 50.0
ENGAGEMENT_STARS_FACTOR = 0.2
ENGAGEMENT_PRESSURE_FACTOR = 25.0
ENGAGEMENT_MIN = 0.0
ENGAGEMENT_MAX = 100.0


def _build_owner_summary(owner: Owner, repositories: list[Repository]) -> OwnerAnalyticsSummary:
    repository_count = len(repositories)
    stars_values = [repository.stars for repository in repositories]
    forks_values = [repository.forks for repository in repositories]
    open_items_values = [repository.open_issues for repository in repositories]

    total_stars = sum(stars_values)
    total_forks = sum(forks_values)
    total_open_items = sum(open_items_values)

    average_stars = (total_stars / repository_count) if repository_count else 0.0
    median_stars = float(median(stars_values)) if repository_count else 0.0
    average_forks = (total_forks / repository_count) if repository_count else 0.0
    issue_pressure = total_open_items / max(total_stars, 1)

    # Engagement score uses stars and issue pressure as a simple comparative heuristic.
    engagement_score = max(
        ENGAGEMENT_MIN,
        min(
            ENGAGEMENT_MAX,
            ENGAGEMENT_BASELINE
            + (average_stars * ENGAGEMENT_STARS_FACTOR)
            - (issue_pressure * ENGAGEMENT_PRESSURE_FACTOR),
        ),
    )

    return OwnerAnalyticsSummary(
        owner_username=owner.username,
        repository_count=repository_count,
        total_stars=total_stars,
        total_forks=total_forks,
        total_open_items=total_open_items,
        average_stars=round(average_stars, 2),
        median_stars=round(median_stars, 2),
        average_forks=round(average_forks, 2),
        issue_pressure=round(issue_pressure, 4),
        engagement_score=round(engagement_score, 2),
    )


def _repositories_for_owner(session: Session, owner: Owner) -> list[Repository]:
    return session.exec(select(Repository).where(Repository.owner_id == owner.id)).all()


def get_owner_summary(owner_username: str, session: Session) -> OwnerAnalyticsSummary:
    owner = session.exec(select(Owner).where(Owner.username == owner_username)).first()
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found.",
        )

    repositories = _repositories_for_owner(session, owner)
    return _build_owner_summary(owner, repositories)


def get_repository_leaderboard(
    session: Session,
    *,
    metric: str = "popularity",
    limit: int = 10,
    offset: int = 0,
    owner_username: str | None = None,
    min_stars: int | None = None,
) -> list[RepositoryLeaderboardItem]:
    popularity_score_expr = (
        Repository.stars + (POPULARITY_FORK_WEIGHT * Repository.forks)
    ).label("popularity_score")
    query = (
        select(Repository, Owner.username, popularity_score_expr)
        .join(Owner, Repository.owner_id == Owner.id)
    )

    if owner_username:
        query = query.where(Owner.username == owner_username)

    if min_stars is not None:
        query = query.where(Repository.stars >= min_stars)

    if metric == "stars":
        query = query.order_by(desc(Repository.stars), Repository.full_name)
    elif metric == "forks":
        query = query.order_by(desc(Repository.forks), Repository.full_name)
    else:
        query = query.order_by(desc(popularity_score_expr), Repository.full_name)

    rows = session.exec(query.offset(offset).limit(limit)).all()
    payload: list[RepositoryLeaderboardItem] = []

    for repository, owner_name, popularity_score in rows:
        pressure = repository.open_issues / max(repository.stars, 1)
        payload.append(
            RepositoryLeaderboardItem(
                full_name=repository.full_name,
                owner_username=owner_name,
                stars=repository.stars,
                forks=repository.forks,
                open_items=repository.open_issues,
                popularity_score=popularity_score,
                issue_pressure=round(pressure, 4),
            )
        )

    return payload


def compare_owners(left_username: str, right_username: str, session: Session) -> OwnerComparison:
    left_summary = get_owner_summary(left_username, session)
    right_summary = get_owner_summary(right_username, session)

    total_stars_tie = left_summary.total_stars == right_summary.total_stars
    winner_by_total_stars: str | None
    if total_stars_tie:
        winner_by_total_stars = None
    elif left_summary.total_stars > right_summary.total_stars:
        winner_by_total_stars = left_summary.owner_username
    else:
        winner_by_total_stars = right_summary.owner_username

    engagement_score_tie = (
        left_summary.engagement_score == right_summary.engagement_score
    )
    winner_by_engagement_score: str | None
    if engagement_score_tie:
        winner_by_engagement_score = None
    elif left_summary.engagement_score > right_summary.engagement_score:
        winner_by_engagement_score = left_summary.owner_username
    else:
        winner_by_engagement_score = right_summary.owner_username

    return OwnerComparison(
        left=left_summary,
        right=right_summary,
        winner_by_total_stars=winner_by_total_stars,
        winner_by_engagement_score=winner_by_engagement_score,
        total_stars_tie=total_stars_tie,
        engagement_score_tie=engagement_score_tie,
    )
