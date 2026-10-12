from fastapi import APIRouter

from app.database import SessionDep
from app.models import IngestionJobRead
from app.services.jobs import get_job as get_job_service

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.get("/{job_id}", response_model=IngestionJobRead)
async def get_job(job_id: str, session: SessionDep) -> IngestionJobRead:
    return get_job_service(job_id, session)
