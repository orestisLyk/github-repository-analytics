from fastapi import HTTPException, status
from sqlmodel import Session

from app.dao import owners as owners_dao
from app.dao import repositories as repositories_dao
from app.models import OwnerCreate, OwnerRead, Repository, RepositoryRead
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
        open_issues=repository.open_issues,
        owner_username=owner_username,
    )


def list_owners(
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    username: str | None = None,
) -> list[OwnerRead]:
    owners = owners_dao.list_owners(
        session,
        limit=limit,
        offset=offset,
        username=username,
    )
    payload: list[OwnerRead] = []

    for owner in owners:
        repositories = owners_dao.list_repositories_for_owner(session, owner.id)
        payload.append(
            OwnerRead(
                id=owner.id,
                username=owner.username,
                url=owner.url,
                repositories=[
                    to_repository_read(repository, owner.username)
                    for repository in repositories
                ],
            )
        )

    return payload


async def _sync_owner_from_url(
    owner_url: str,
    session: Session,
    *,
    conflict_if_exists: bool,
) -> OwnerRead:
    service = GitHubService()
    try:
        owner_data = await service.get_owner(owner_url)
        repositories_data = await service.list_owner_repositories(owner_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        await service.close()

    existing_owner = owners_dao.get_owner_by_username(session, owner_data["username"])
    if existing_owner and conflict_if_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner already exists.",
        )

    if existing_owner:
        owner = owners_dao.update_owner_url(session, existing_owner, owner_data["url"])
    else:
        owner = owners_dao.create_owner(
            session,
            username=owner_data["username"],
            url=owner_data["url"],
        )

    repositories_dao.upsert_repositories_for_owner(session, owner.id, repositories_data)

    owner_repositories = owners_dao.list_repositories_for_owner(session, owner.id)

    return OwnerRead(
        id=owner.id,
        username=owner.username,
        url=owner.url,
        repositories=[
            to_repository_read(repository, owner.username)
            for repository in owner_repositories
        ],
    )


async def create_owner(owner_create: OwnerCreate, session: Session) -> OwnerRead:
    return await _sync_owner_from_url(
        str(owner_create.url),
        session,
        conflict_if_exists=True,
    )


async def ingest_owner_url(owner_url: str, session: Session) -> OwnerRead:
    return await _sync_owner_from_url(owner_url, session, conflict_if_exists=False)


async def refresh_owner(owner_username: str, session: Session) -> OwnerRead:
    owner_url = f"https://github.com/{owner_username}"
    return await _sync_owner_from_url(owner_url, session, conflict_if_exists=False)
