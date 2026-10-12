from sqlalchemy import desc
from sqlmodel import Session, select

from app.models import Owner, Repository


def list_repositories(
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    owner_username: str | None = None,
    min_stars: int | None = None,
    sort: str = "stars_desc",
) -> list[Repository]:
    query = select(Repository)

    if owner_username:
        owner = session.exec(select(Owner).where(Owner.username == owner_username)).first()
        if owner is None:
            return []
        query = query.where(Repository.owner_id == owner.id)

    if min_stars is not None:
        query = query.where(Repository.stars >= min_stars)

    if sort == "stars_asc":
        query = query.order_by(Repository.stars, Repository.full_name)
    elif sort == "name_asc":
        query = query.order_by(Repository.full_name)
    elif sort == "name_desc":
        query = query.order_by(desc(Repository.full_name))
    else:
        query = query.order_by(desc(Repository.stars), Repository.full_name)

    query = query.offset(offset).limit(limit)
    return session.exec(query).all()


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


def upsert_repositories_for_owner(
    session: Session,
    owner_id: int,
    repositories_data: list[dict],
) -> None:
    for repository_data in repositories_data:
        existing = get_repository_by_full_name(session, repository_data["full_name"])
        if existing:
            existing.name = repository_data["name"]
            existing.url = repository_data["url"]
            existing.description = repository_data.get("description")
            existing.stars = repository_data.get("stars", 0)
            existing.forks = repository_data.get("forks", 0)
            existing.open_issues = repository_data.get("open_issues", 0)
            existing.owner_id = owner_id
            session.add(existing)
            continue

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


def upsert_repository(
    session: Session,
    *,
    full_name: str,
    name: str,
    url: str,
    description: str | None,
    stars: int,
    forks: int,
    open_issues: int,
    owner_id: int,
) -> Repository:
    existing = get_repository_by_full_name(session, full_name)
    if existing:
        existing.name = name
        existing.url = url
        existing.description = description
        existing.stars = stars
        existing.forks = forks
        existing.open_issues = open_issues
        existing.owner_id = owner_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    return create_repository(
        session,
        name=name,
        full_name=full_name,
        url=url,
        description=description,
        stars=stars,
        forks=forks,
        open_issues=open_issues,
        owner_id=owner_id,
    )
