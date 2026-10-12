from fastapi import APIRouter, BackgroundTasks, Query, status

from app.database import SessionDep
from app.models import IngestionJobRead, OwnerCreate, OwnerRead
from app.services.jobs import create_owner_ingestion_job
from app.services.jobs import process_owner_ingestion_job
from app.services.owners import create_owner as create_owner_service
from app.services.owners import list_owners as list_owners_service
from app.services.owners import refresh_owner as refresh_owner_service

router = APIRouter(
    prefix="/owners",
    tags=["Owners"],
)

@router.get("/", response_model=list[OwnerRead])
async def read_owners(
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    username: str | None = Query(default=None),
) -> list[OwnerRead]:
    return list_owners_service(
        session,
        limit=limit,
        offset=offset,
        username=username,
    )


@router.post("/", response_model=OwnerRead, status_code=status.HTTP_201_CREATED)
async def create_owner(owner_create: OwnerCreate, session: SessionDep) -> OwnerRead:
    return await create_owner_service(owner_create, session)


@router.post("/ingest", response_model=IngestionJobRead, status_code=status.HTTP_202_ACCEPTED)
async def ingest_owner(
    owner_create: OwnerCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> IngestionJobRead:
    owner_url = str(owner_create.url)
    job = create_owner_ingestion_job(owner_url, session)
    background_tasks.add_task(process_owner_ingestion_job, job.id, owner_url)
    return job


@router.post("/{owner_username}/refresh", response_model=OwnerRead)
async def refresh_owner(owner_username: str, session: SessionDep) -> OwnerRead:
    return await refresh_owner_service(owner_username, session)