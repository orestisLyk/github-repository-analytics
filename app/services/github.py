from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Any

import httpx
from fastapi import HTTPException, status


class GitHubService:
	"""Thin async client for the GitHub REST API."""

	def __init__(self, timeout: float = 15.0) -> None:
		token = os.getenv("GITHUB_TOKEN")
		headers = {
			"Accept": "application/vnd.github+json",
			"User-Agent": "github-repository-analytics",
		}
		if token:
			headers["Authorization"] = f"Bearer {token}"

		self._client = httpx.AsyncClient(
			base_url="https://api.github.com",
			headers=headers,
			timeout=timeout,
		)

	async def close(self) -> None:
		await self._client.aclose()

	async def _request_get(
		self,
		path: str,
		*,
		params: dict[str, Any] | None = None,
		not_found_detail: str = "Resource not found on GitHub.",
	) -> httpx.Response:
		try:
			response = await self._client.get(path, params=params)
		except httpx.RequestError as exc:
			raise HTTPException(
				status_code=status.HTTP_502_BAD_GATEWAY,
				detail="Could not reach GitHub API.",
			) from exc

		if response.status_code == status.HTTP_404_NOT_FOUND:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail=not_found_detail,
			)

		if response.status_code == status.HTTP_403_FORBIDDEN:
			if response.headers.get("x-ratelimit-remaining") == "0":
				raise HTTPException(
					status_code=status.HTTP_429_TOO_MANY_REQUESTS,
					detail="GitHub API rate limit exceeded.",
				)
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail="GitHub API request was forbidden.",
			)

		if response.is_error:
			raise HTTPException(
				status_code=status.HTTP_502_BAD_GATEWAY,
				detail=f"GitHub API error ({response.status_code}).",
			)

		return response

	async def _get(self, path: str) -> dict:
		response = await self._request_get(path)

		payload = response.json()
		if not isinstance(payload, dict):
			raise HTTPException(
				status_code=status.HTTP_502_BAD_GATEWAY,
				detail="Unexpected response from GitHub API.",
			)

		return payload

	@staticmethod
	def parse_owner_url(url: str) -> str:
		parsed = urlparse(url)
		parts = [part for part in parsed.path.strip("/").split("/") if part]
		if parsed.netloc != "github.com" or len(parts) != 1:
			raise ValueError("Expected a GitHub owner URL like https://github.com/username")
		return parts[0]

	@staticmethod
	def parse_repository_url(url: str) -> tuple[str, str]:
		parsed = urlparse(url)
		parts = [part for part in parsed.path.strip("/").split("/") if part]
		if parsed.netloc != "github.com" or len(parts) != 2:
			raise ValueError("Expected a GitHub repository URL like https://github.com/owner/repo")
		return parts[0], parts[1]

	async def get_owner(self, owner_url: str) -> dict:
		username = self.parse_owner_url(owner_url)
		owner = await self._get(f"/users/{username}")
		return {
			"username": owner["login"],
			"url": owner["html_url"],
		}

	async def get_repository(self, repository_url: str) -> dict:
		owner, repo = self.parse_repository_url(repository_url)
		repository = await self._get(f"/repos/{owner}/{repo}")
		return {
			"name": repository["name"],
			"full_name": repository["full_name"],
			"url": repository["html_url"],
			"description": repository.get("description"),
			"stars": repository.get("stargazers_count", 0),
			"forks": repository.get("forks_count", 0),
			"open_issues": repository.get("open_issues_count", 0),
			"owner_username": repository["owner"]["login"],
		}

	async def list_owner_repositories(self, owner_url: str) -> list[dict]:
		username = self.parse_owner_url(owner_url)
		repositories: list[dict] = []
		page = 1

		while True:
			response = await self._request_get(
				f"/users/{username}/repos",
				params={
					"type": "owner",
					"sort": "updated",
					"per_page": 100,
					"page": page,
				},
				not_found_detail="Owner not found on GitHub.",
			)

			payload = response.json()
			if not isinstance(payload, list):
				raise HTTPException(
					status_code=status.HTTP_502_BAD_GATEWAY,
					detail="Unexpected response from GitHub API.",
				)

			if not payload:
				break

			for repository in payload:
				repositories.append(
					{
						"name": repository["name"],
						"full_name": repository["full_name"],
						"url": repository["html_url"],
						"description": repository.get("description"),
						"stars": repository.get("stargazers_count", 0),
						"forks": repository.get("forks_count", 0),
						"open_issues": repository.get("open_issues_count", 0),
						"owner_username": username,
					}
				)

			page += 1

		return repositories

