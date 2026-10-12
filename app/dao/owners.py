from sqlmodel import Session, select

from app.models import Owner, Repository


def list_owners(session: Session) -> list[Owner]:
    return session.exec(select(Owner)).all()


def get_owner_by_username(session: Session, username: str) -> Owner | None:
    return session.exec(select(Owner).where(Owner.username == username)).first()


def create_owner(session: Session, username: str, url: str) -> Owner:
    owner = Owner(username=username, url=url)
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return owner


def list_repositories_for_owner(session: Session, owner_id: int) -> list[Repository]:
    return session.exec(select(Repository).where(Repository.owner_id == owner_id)).all()
