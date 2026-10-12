from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.routers.owners import router as owners_router
from app.routers.repositories import router as repositories_router
from app.services.github import GitHubService


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _override_get_session():
    with Session(test_engine) as session:
        yield session


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(owners_router)
    app.include_router(repositories_router)
    app.dependency_overrides[get_session] = _override_get_session
    return TestClient(app)


def setup_function() -> None:
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)


async def _fake_get_owner(self, owner_url: str) -> dict:
    return {
        "username": "tiangolo",
        "url": "https://github.com/tiangolo",
    }


async def _fake_list_owner_repositories(self, owner_url: str) -> list[dict]:
    return [
        {
            "name": "fastapi",
            "full_name": "tiangolo/fastapi",
            "url": "https://github.com/tiangolo/fastapi",
            "description": "FastAPI framework",
            "stars": 100,
            "forks": 20,
            "open_issues": 5,
            "owner_username": "tiangolo",
        }
    ]


async def _fake_get_repository(self, repository_url: str) -> dict:
    return {
        "name": "sqlmodel",
        "full_name": "fastapi/sqlmodel",
        "url": "https://github.com/fastapi/sqlmodel",
        "description": "SQL databases in Python",
        "stars": 50,
        "forks": 10,
        "open_issues": 2,
        "owner_username": "fastapi",
    }


async def _fake_close(self) -> None:
    return None


def test_create_owner_stores_owner_and_repositories(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    response = client.post(
        "/owners/",
        json={"url": "https://github.com/tiangolo"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "tiangolo"
    assert len(payload["repositories"]) == 1
    assert payload["repositories"][0]["full_name"] == "tiangolo/fastapi"

    list_response = client.get("/owners/")
    assert list_response.status_code == 200
    owners = list_response.json()
    assert len(owners) == 1


def test_create_owner_returns_conflict_on_duplicate(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    first_response = client.post(
        "/owners/",
        json={"url": "https://github.com/tiangolo"},
    )
    second_response = client.post(
        "/owners/",
        json={"url": "https://github.com/tiangolo"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_create_repository_autocreates_owner(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_repository", _fake_get_repository)
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    response = client.post(
        "/repositories/",
        json={"url": "https://github.com/fastapi/sqlmodel"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["full_name"] == "fastapi/sqlmodel"
    assert payload["owner_username"] == "fastapi"

    list_response = client.get("/repositories/")
    assert list_response.status_code == 200
    repositories = list_response.json()
    assert len(repositories) == 1
