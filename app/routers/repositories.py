from typing import Literal

from fastapi import APIRouter, Query, status

from app.database import SessionDep
from app.models import RepositoryCreate, RepositoryRead
from app.services.repositories import create_repository as create_repository_service
from app.services.repositories import list_repositories as list_repositories_service
from app.services.repositories import refresh_repository as refresh_repository_service

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)

@router.get("/", response_model=list[RepositoryRead])
async def read_repositories(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    owner_username: str | None = Query(default=None),
    min_stars: int | None = Query(default=None, ge=0),
    sort: Literal["stars_desc", "stars_asc", "name_asc", "name_desc"] = Query(
        default="stars_desc"
    ),
) -> list[RepositoryRead]:
    return list_repositories_service(
        session,
        limit=limit,
        offset=offset,
        owner_username=owner_username,
        min_stars=min_stars,
        sort=sort,
    )


@router.post("/", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repository_create: RepositoryCreate,
    session: SessionDep,
) -> RepositoryRead:
    return await create_repository_service(repository_create, session)


@router.post("/{owner_username}/{repository_name}/refresh", response_model=RepositoryRead)
async def refresh_repository(
    owner_username: str,
    repository_name: str,
    session: SessionDep,
) -> RepositoryRead:
    return await refresh_repository_service(owner_username, repository_name, session)