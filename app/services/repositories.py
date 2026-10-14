from fastapi import HTTPException, status
from sqlmodel import Session

from app.dao import repositories as repositories_dao
from app.models import Repository, RepositoryCreate, RepositoryRead
from app.services.github import GitHubService


def to_repository_read(repository: Repository, owner_username: str) -> RepositoryRead:
    return RepositoryRead(
        id=repository.id,
        name=repository.name,
        full_name=repository.full_name,
        url=repository.url,
        description=repository.description,
        stars=repository.stars,
        forks=repository.forks,
        open_items=repository.open_issues,
        owner_username=owner_username,
    )

def list_repositories(
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    owner_username: str | None = None,
    min_stars: int | None = None,
    sort: str = "stars_desc",
) -> list[RepositoryRead]:
    repository_rows = repositories_dao.list_repositories(
        session,
        limit=limit,
        offset=offset,
        owner_username=owner_username,
        min_stars=min_stars,
        sort=sort,
    )
    return [
        to_repository_read(repository, owner_name)
        for repository, owner_name in repository_rows
    ]


async def create_repository(
    repository_create: RepositoryCreate,
    session: Session,
) -> RepositoryRead:
    service = GitHubService()
    try:
        repository_data = await service.get_repository(str(repository_create.url))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        await service.close()

    existing_repository = repositories_dao.get_repository_by_full_name(
        session,
        repository_data["full_name"],
    )
    if existing_repository:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository already exists.",
        )

    owner_username = repository_data["owner_username"]
    owner = repositories_dao.get_or_create_owner_by_username(session, owner_username)

    repository = repositories_dao.create_repository(
        session,
        name=repository_data["name"],
        full_name=repository_data["full_name"],
        url=repository_data["url"],
        description=repository_data.get("description"),
        stars=repository_data.get("stars", 0),
        forks=repository_data.get("forks", 0),
        open_issues=repository_data.get("open_issues", 0),
        owner_id=owner.id,
    )

    return to_repository_read(repository, owner.username)


async def refresh_repository(
    owner_username: str,
    repository_name: str,
    session: Session,
) -> RepositoryRead:
    service = GitHubService()
    repository_url = f"https://github.com/{owner_username}/{repository_name}"
    try:
        repository_data = await service.get_repository(repository_url)
    finally:
        await service.close()

    owner = repositories_dao.get_or_create_owner_by_username(
        session,
        repository_data["owner_username"],
    )

    repository = repositories_dao.upsert_repository(
        session,
        name=repository_data["name"],
        full_name=repository_data["full_name"],
        url=repository_data["url"],
        description=repository_data.get("description"),
        stars=repository_data.get("stars", 0),
        forks=repository_data.get("forks", 0),
        open_issues=repository_data.get("open_issues", 0),
        owner_id=owner.id,
    )

    return to_repository_read(repository, owner.username)
