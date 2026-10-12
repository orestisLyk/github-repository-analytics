from fastapi import APIRouter, status

from app.database import SessionDep
from app.models import RepositoryCreate, RepositoryRead
from app.services.repositories import create_repository as create_repository_service
from app.services.repositories import list_repositories as list_repositories_service

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)

@router.get("/", response_model=list[RepositoryRead])
async def read_repositories(session: SessionDep) -> list[RepositoryRead]:
    return list_repositories_service(session)


@router.post("/", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repository_create: RepositoryCreate,
    session: SessionDep,
) -> RepositoryRead:
    return await create_repository_service(repository_create, session)