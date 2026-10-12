from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import IngestionJob


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_job(session: Session, *, kind: str, target: str) -> IngestionJob:
    job = IngestionJob(kind=kind, target=target)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job_by_id(session: Session, job_id: str) -> IngestionJob | None:
    return session.exec(select(IngestionJob).where(IngestionJob.id == job_id)).first()


def set_job_status(
    session: Session,
    job: IngestionJob,
    *,
    status: str,
    error_message: str | None = None,
) -> IngestionJob:
    job.status = status
    job.error_message = error_message
    job.updated_at = utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
