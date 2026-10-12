from fastapi import HTTPException, status
from sqlmodel import Session

from app.dao import jobs as jobs_dao
from app.database import engine
from app.models import IngestionJobRead
from app.services.owners import ingest_owner_url


def _default_job_session_factory() -> Session:
    return Session(engine)


JOB_SESSION_FACTORY = _default_job_session_factory


def to_ingestion_job_read(job) -> IngestionJobRead:
    return IngestionJobRead(
        id=job.id,
        kind=job.kind,
        target=job.target,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def create_owner_ingestion_job(owner_url: str, session: Session) -> IngestionJobRead:
    job = jobs_dao.create_job(
        session,
        kind="owner_ingestion",
        target=owner_url,
    )
    return to_ingestion_job_read(job)


def get_job(job_id: str, session: Session) -> IngestionJobRead:
    job = jobs_dao.get_job_by_id(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return to_ingestion_job_read(job)


async def process_owner_ingestion_job(job_id: str, owner_url: str) -> None:
    with JOB_SESSION_FACTORY() as session:
        job = jobs_dao.get_job_by_id(session, job_id)
        if job is None:
            return

        jobs_dao.set_job_status(session, job, status="running")
        try:
            await ingest_owner_url(owner_url, session)
            jobs_dao.set_job_status(session, job, status="completed")
        except Exception as exc:
            jobs_dao.set_job_status(
                session,
                job,
                status="failed",
                error_message=str(exc),
            )
