from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.routers.analytics import router as analytics_router
from app.routers.jobs import router as jobs_router
from app.routers.owners import router as owners_router
from app.routers.repositories import router as repositories_router
from app.services import jobs as jobs_service
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
    app.include_router(jobs_router)
    app.include_router(analytics_router)
    app.dependency_overrides[get_session] = _override_get_session
    jobs_service.JOB_SESSION_FACTORY = lambda: Session(test_engine)
    return TestClient(app)


def setup_function() -> None:
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    REPO_STARS["tiangolo/fastapi"] = 100
    REPO_STARS["fastapi/sqlmodel"] = 50


REPO_STARS: dict[str, int] = {
    "tiangolo/fastapi": 100,
    "fastapi/sqlmodel": 50,
}


def _owner_from_url(owner_url: str) -> str:
    return owner_url.rstrip("/").split("/")[-1]


def _owner_repo_name(owner_username: str) -> str:
    if owner_username == "tiangolo":
        return "fastapi"
    return "sample"


async def _fake_get_owner(self, owner_url: str) -> dict:
    owner_username = _owner_from_url(owner_url)
    return {
        "username": owner_username,
        "url": f"https://github.com/{owner_username}",
    }


async def _fake_list_owner_repositories(self, owner_url: str) -> list[dict]:
    owner_username = _owner_from_url(owner_url)
    repository_name = _owner_repo_name(owner_username)
    full_name = f"{owner_username}/{repository_name}"
    return [
        {
            "name": repository_name,
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": "FastAPI framework",
            "stars": REPO_STARS.get(full_name, 0),
            "forks": 20,
            "open_issues": 5,
            "owner_username": owner_username,
        }
    ]


async def _fake_get_repository(self, repository_url: str) -> dict:
    owner_username, repository_name = repository_url.rstrip("/").split("/")[-2:]
    full_name = f"{owner_username}/{repository_name}"
    return {
        "name": repository_name,
        "full_name": full_name,
        "url": f"https://github.com/{full_name}",
        "description": "SQL databases in Python",
        "stars": REPO_STARS.get(full_name, 0),
        "forks": 10,
        "open_issues": 2,
        "owner_username": owner_username,
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
    assert payload["repositories"][0]["open_items"] == 5

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


def test_ingest_owner_creates_job_and_status(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    response = client.post(
        "/owners/ingest",
        json={"url": "https://github.com/tiangolo"},
    )

    assert response.status_code == 202
    job = response.json()
    assert job["kind"] == "owner_ingestion"
    assert job["target"] == "https://github.com/tiangolo"

    status_response = client.get(f"/jobs/{job['id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] in {"pending", "running", "completed"}


def test_refresh_owner_updates_repository_stats(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    create_response = client.post(
        "/owners/",
        json={"url": "https://github.com/tiangolo"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["repositories"][0]["stars"] == 100

    REPO_STARS["tiangolo/fastapi"] = 999
    refresh_response = client.post("/owners/tiangolo/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["repositories"][0]["stars"] == 999


def test_refresh_repository_updates_stats(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_repository", _fake_get_repository)
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()

    create_response = client.post(
        "/repositories/",
        json={"url": "https://github.com/fastapi/sqlmodel"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["stars"] == 50

    REPO_STARS["fastapi/sqlmodel"] = 250
    refresh_response = client.post("/repositories/fastapi/sqlmodel/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["stars"] == 250


def test_list_endpoints_pagination_and_filters(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()
    REPO_STARS["tiangolo/fastapi"] = 300

    response_one = client.post(
        "/owners/",
        json={"url": "https://github.com/tiangolo"},
    )
    assert response_one.status_code == 201

    response_two = client.post(
        "/owners/",
        json={"url": "https://github.com/pydantic"},
    )
    assert response_two.status_code == 201

    owners_page = client.get("/owners/?limit=1&offset=0")
    assert owners_page.status_code == 200
    assert len(owners_page.json()) == 1

    filtered_owners = client.get("/owners/?username=pyd")
    assert filtered_owners.status_code == 200
    assert len(filtered_owners.json()) == 1
    assert filtered_owners.json()[0]["username"] == "pydantic"

    filtered_repositories = client.get(
        "/repositories/?owner_username=tiangolo&min_stars=200&sort=stars_desc"
    )
    assert filtered_repositories.status_code == 200
    assert len(filtered_repositories.json()) == 1
    assert filtered_repositories.json()[0]["full_name"] == "tiangolo/fastapi"


def test_owner_summary_analytics(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()
    REPO_STARS["tiangolo/fastapi"] = 300
    create_response = client.post("/owners/", json={"url": "https://github.com/tiangolo"})
    assert create_response.status_code == 201

    summary_response = client.get("/analytics/owners/tiangolo/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["owner_username"] == "tiangolo"
    assert summary["repository_count"] == 1
    assert summary["total_stars"] == 300
    assert summary["median_stars"] == 300.0


def test_repository_leaderboard_analytics(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()
    REPO_STARS["tiangolo/fastapi"] = 400
    REPO_STARS["pydantic/sample"] = 150
    assert client.post("/owners/", json={"url": "https://github.com/tiangolo"}).status_code == 201
    assert client.post("/owners/", json={"url": "https://github.com/pydantic"}).status_code == 201

    leaderboard_response = client.get("/analytics/repositories/leaderboard?metric=stars&limit=1")
    assert leaderboard_response.status_code == 200
    leaderboard = leaderboard_response.json()
    assert len(leaderboard) == 1
    assert leaderboard[0]["full_name"] == "tiangolo/fastapi"


def test_owner_comparison_analytics(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()
    REPO_STARS["tiangolo/fastapi"] = 500
    REPO_STARS["pydantic/sample"] = 200
    assert client.post("/owners/", json={"url": "https://github.com/tiangolo"}).status_code == 201
    assert client.post("/owners/", json={"url": "https://github.com/pydantic"}).status_code == 201

    comparison_response = client.get("/analytics/owners/compare?left=tiangolo&right=pydantic")
    assert comparison_response.status_code == 200
    comparison = comparison_response.json()
    assert comparison["left"]["owner_username"] == "tiangolo"
    assert comparison["right"]["owner_username"] == "pydantic"
    assert comparison["winner_by_total_stars"] == "tiangolo"
    assert comparison["total_stars_tie"] is False
    assert comparison["engagement_score_tie"] is False


def test_owner_comparison_analytics_tie(monkeypatch) -> None:
    monkeypatch.setattr(GitHubService, "get_owner", _fake_get_owner)
    monkeypatch.setattr(
        GitHubService,
        "list_owner_repositories",
        _fake_list_owner_repositories,
    )
    monkeypatch.setattr(GitHubService, "close", _fake_close)

    client = _build_test_client()
    REPO_STARS["tiangolo/fastapi"] = 250
    REPO_STARS["pydantic/sample"] = 250
    assert client.post("/owners/", json={"url": "https://github.com/tiangolo"}).status_code == 201
    assert client.post("/owners/", json={"url": "https://github.com/pydantic"}).status_code == 201

    comparison_response = client.get("/analytics/owners/compare?left=tiangolo&right=pydantic")
    assert comparison_response.status_code == 200
    comparison = comparison_response.json()
    assert comparison["winner_by_total_stars"] is None
    assert comparison["winner_by_engagement_score"] is None
    assert comparison["total_stars_tie"] is True
    assert comparison["engagement_score_tie"] is True
