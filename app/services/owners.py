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


def list_owners(session: Session) -> list[OwnerRead]:
    owners = owners_dao.list_owners(session)
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


async def create_owner(owner_create: OwnerCreate, session: Session) -> OwnerRead:
    service = GitHubService()
    try:
        owner_data = await service.get_owner(str(owner_create.url))
        repositories_data = await service.list_owner_repositories(str(owner_create.url))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        await service.close()

    existing_owner = owners_dao.get_owner_by_username(session, owner_data["username"])
    if existing_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner already exists.",
        )

    owner = owners_dao.create_owner(
        session,
        username=owner_data["username"],
        url=owner_data["url"],
    )
    repositories_dao.create_repositories_for_owner(session, owner.id, repositories_data)

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
