from statistics import median

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import (
    Owner,
    OwnerAnalyticsSummary,
    OwnerComparison,
    Repository,
    RepositoryLeaderboardItem,
)


def _build_owner_summary(owner: Owner, repositories: list[Repository]) -> OwnerAnalyticsSummary:
    repository_count = len(repositories)
    stars_values = [repository.stars for repository in repositories]
    forks_values = [repository.forks for repository in repositories]
    issues_values = [repository.open_issues for repository in repositories]

    total_stars = sum(stars_values)
    total_forks = sum(forks_values)
    total_open_issues = sum(issues_values)

    average_stars = (total_stars / repository_count) if repository_count else 0.0
    median_stars = float(median(stars_values)) if repository_count else 0.0
    average_forks = (total_forks / repository_count) if repository_count else 0.0
    issue_pressure = total_open_issues / max(total_stars, 1)

    # Health score balances popularity and operational load on a simple 0-100 scale.
    health_score = max(0.0, min(100.0, 50.0 + average_stars * 0.2 - issue_pressure * 25.0))

    return OwnerAnalyticsSummary(
        owner_username=owner.username,
        repository_count=repository_count,
        total_stars=total_stars,
        total_forks=total_forks,
        total_open_issues=total_open_issues,
        average_stars=round(average_stars, 2),
        median_stars=round(median_stars, 2),
        average_forks=round(average_forks, 2),
        issue_pressure=round(issue_pressure, 4),
        health_score=round(health_score, 2),
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
    repositories = session.exec(select(Repository)).all()

    if owner_username:
        owner = session.exec(select(Owner).where(Owner.username == owner_username)).first()
        if owner is None:
            return []
        repositories = [repository for repository in repositories if repository.owner_id == owner.id]

    if min_stars is not None:
        repositories = [repository for repository in repositories if repository.stars >= min_stars]

    def popularity_score(repository: Repository) -> int:
        return repository.stars + (2 * repository.forks)

    if metric == "stars":
        repositories.sort(key=lambda repository: (repository.stars, repository.full_name), reverse=True)
    elif metric == "forks":
        repositories.sort(key=lambda repository: (repository.forks, repository.full_name), reverse=True)
    else:
        repositories.sort(key=lambda repository: (popularity_score(repository), repository.full_name), reverse=True)

    sliced = repositories[offset : offset + limit]
    payload: list[RepositoryLeaderboardItem] = []

    for repository in sliced:
        owner = session.get(Owner, repository.owner_id)
        owner_name = owner.username if owner else "unknown"
        pressure = repository.open_issues / max(repository.stars, 1)
        payload.append(
            RepositoryLeaderboardItem(
                full_name=repository.full_name,
                owner_username=owner_name,
                stars=repository.stars,
                forks=repository.forks,
                open_issues=repository.open_issues,
                popularity_score=popularity_score(repository),
                issue_pressure=round(pressure, 4),
            )
        )

    return payload


def compare_owners(left_username: str, right_username: str, session: Session) -> OwnerComparison:
    left_summary = get_owner_summary(left_username, session)
    right_summary = get_owner_summary(right_username, session)

    winner_by_total_stars = left_summary.owner_username
    if right_summary.total_stars > left_summary.total_stars:
        winner_by_total_stars = right_summary.owner_username

    winner_by_health_score = left_summary.owner_username
    if right_summary.health_score > left_summary.health_score:
        winner_by_health_score = right_summary.owner_username

    return OwnerComparison(
        left=left_summary,
        right=right_summary,
        winner_by_total_stars=winner_by_total_stars,
        winner_by_health_score=winner_by_health_score,
    )
