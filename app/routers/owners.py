from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.database import SessionDep
from app.models import Owner, OwnerCreate, OwnerRead, Repository, RepositoryRead
from app.services.github import GitHubService

router = APIRouter(
    prefix="/owners",
    tags=["Owners"],
)


def _to_repository_read(repository: Repository, owner_username: str) -> RepositoryRead:
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


@router.get("/", response_model=list[OwnerRead])
async def read_owners(session: SessionDep) -> list[OwnerRead]:
    owners = session.exec(select(Owner)).all()
    payload: list[OwnerRead] = []

    for owner in owners:
        repositories = session.exec(
            select(Repository).where(Repository.owner_id == owner.id)
        ).all()
        payload.append(
            OwnerRead(
                id=owner.id,
                username=owner.username,
                url=owner.url,
                repositories=[
                    _to_repository_read(repository, owner.username)
                    for repository in repositories
                ],
            )
        )

    return payload


@router.post("/", response_model=OwnerRead, status_code=status.HTTP_201_CREATED)
async def create_owner(owner_create: OwnerCreate, session: SessionDep) -> OwnerRead:
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

    existing_owner = session.exec(
        select(Owner).where(Owner.username == owner_data["username"])
    ).first()
    if existing_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner already exists.",
        )

    owner = Owner(username=owner_data["username"], url=owner_data["url"])
    session.add(owner)
    session.commit()
    session.refresh(owner)

    for repository_data in repositories_data:
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

    owner_repositories = session.exec(
        select(Repository).where(Repository.owner_id == owner.id)
    ).all()

    return OwnerRead(
        id=owner.id,
        username=owner.username,
        url=owner.url,
        repositories=[
            _to_repository_read(repository, owner.username)
            for repository in owner_repositories
        ],
    )