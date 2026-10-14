import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.services.github import GitHubService


def _build_response(status_code: int, payload, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://api.github.com/mock")
    return httpx.Response(status_code=status_code, json=payload, headers=headers, request=request)


def test_list_owner_repositories_paginates_all_pages(monkeypatch) -> None:
    service = GitHubService()

    call_pages: list[int] = []

    async def fake_get(path: str, params=None):
        assert path == "/users/tiangolo/repos"
        page = int(params["page"])
        call_pages.append(page)

        if page == 1:
            return _build_response(
                200,
                [
                    {
                        "name": "fastapi",
                        "full_name": "tiangolo/fastapi",
                        "html_url": "https://github.com/tiangolo/fastapi",
                        "description": "FastAPI framework",
                        "stargazers_count": 1,
                        "forks_count": 2,
                        "open_issues_count": 3,
                    }
                ],
            )
        if page == 2:
            return _build_response(
                200,
                [
                    {
                        "name": "typer",
                        "full_name": "tiangolo/typer",
                        "html_url": "https://github.com/tiangolo/typer",
                        "description": "Typer framework",
                        "stargazers_count": 4,
                        "forks_count": 5,
                        "open_issues_count": 6,
                    }
                ],
            )
        return _build_response(200, [])

    monkeypatch.setattr(service._client, "get", fake_get)

    try:
        repositories = asyncio.run(service.list_owner_repositories("https://github.com/tiangolo"))
    finally:
        asyncio.run(service.close())

    assert call_pages == [1, 2, 3]
    assert len(repositories) == 2
    assert repositories[0]["full_name"] == "tiangolo/fastapi"
    assert repositories[1]["full_name"] == "tiangolo/typer"


def test_list_owner_repositories_rate_limit_raises_429(monkeypatch) -> None:
    service = GitHubService()

    async def fake_get(path: str, params=None):
        return _build_response(
            403,
            {"message": "API rate limit exceeded"},
            headers={"x-ratelimit-remaining": "0"},
        )

    monkeypatch.setattr(service._client, "get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_owner_repositories("https://github.com/tiangolo"))

    assert exc_info.value.status_code == 429
    assert "rate limit" in exc_info.value.detail.lower()

    asyncio.run(service.close())


def test_list_owner_repositories_forbidden_non_rate_limit_raises_403(monkeypatch) -> None:
    service = GitHubService()

    async def fake_get(path: str, params=None):
        return _build_response(
            403,
            {"message": "forbidden"},
            headers={"x-ratelimit-remaining": "5"},
        )

    monkeypatch.setattr(service._client, "get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_owner_repositories("https://github.com/tiangolo"))

    assert exc_info.value.status_code == 403

    asyncio.run(service.close())
