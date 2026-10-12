from sqlmodel import Session, select

from app.models import Owner, Repository


def list_repositories(session: Session) -> list[Repository]:
    return session.exec(select(Repository)).all()


def get_repository_by_full_name(session: Session, full_name: str) -> Repository | None:
    return session.exec(select(Repository).where(Repository.full_name == full_name)).first()


def create_repository(
    session: Session,
    *,
    name: str,
    full_name: str,
    url: str,
    description: str | None,
    stars: int,
    forks: int,
    open_issues: int,
    owner_id: int,
) -> Repository:
    repository = Repository(
        name=name,
        full_name=full_name,
        url=url,
        description=description,
        stars=stars,
        forks=forks,
        open_issues=open_issues,
        owner_id=owner_id,
    )
    session.add(repository)
    session.commit()
    session.refresh(repository)
    return repository


def create_repositories_for_owner(
    session: Session,
    owner_id: int,
    repositories_data: list[dict],
) -> None:
    for repository_data in repositories_data:
        repository = Repository(
            name=repository_data["name"],
            full_name=repository_data["full_name"],
            url=repository_data["url"],
            description=repository_data.get("description"),
            stars=repository_data.get("stars", 0),
            forks=repository_data.get("forks", 0),
            open_issues=repository_data.get("open_issues", 0),
            owner_id=owner_id,
        )
        session.add(repository)

    session.commit()


def get_or_create_owner_by_username(session: Session, username: str) -> Owner:
    owner = session.exec(select(Owner).where(Owner.username == username)).first()
    if owner is None:
        owner = Owner(username=username, url=f"https://github.com/{username}")
        session.add(owner)
        session.commit()
        session.refresh(owner)
    return owner
