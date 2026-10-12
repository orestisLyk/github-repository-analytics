from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Owner, Repository, RepositoryCreate, RepositoryRead
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


def list_repositories(session: Session) -> list[RepositoryRead]:
    repositories = session.exec(select(Repository)).all()
    payload: list[RepositoryRead] = []

    for repository in repositories:
        owner = session.get(Owner, repository.owner_id)
        owner_username = owner.username if owner else "unknown"
        payload.append(to_repository_read(repository, owner_username))

    return payload


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

    existing_repository = session.exec(
        select(Repository).where(Repository.full_name == repository_data["full_name"])
    ).first()
    if existing_repository:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository already exists.",
        )

    owner_username = repository_data["owner_username"]
    owner = session.exec(select(Owner).where(Owner.username == owner_username)).first()
    if owner is None:
        owner = Owner(
            username=owner_username,
            url=f"https://github.com/{owner_username}",
        )
        session.add(owner)
        session.commit()
        session.refresh(owner)

    repository = Repository(
        name=repository_data["name"],
        full_name=repository_data["full_name"],
        url=repository_data["url"],
        description=repository_data.get("description"),
        stars=repository_data.get("stars", 0),
        forks=repository_data.get("forks", 0),
        open_issues=repository_data.get("open_issues", 0),
        owner_id=owner.id,
    )
    session.add(repository)
    session.commit()
    session.refresh(repository)

    return to_repository_read(repository, owner.username)
