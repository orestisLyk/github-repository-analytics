from __future__ import annotations

from sqlmodel import Relationship, SQLModel, Field
from pydantic import HttpUrl, field_validator

# Owner model and schemas
class BaseOwner(SQLModel):
    username: str
    url: HttpUrl


class Owner(BaseOwner, table=True):
    id: int | None = Field(default=None, primary_key=True)
    repositories: list["Repository"] = Relationship(back_populates="owner")


class OwnerCreate(SQLModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: HttpUrl) -> HttpUrl:
        parts = v.path.strip("/").split("/")

        if v.host != "github.com" or len(parts) != 1 or not all(parts):
            raise ValueError(
                "URL must point to a GitHub user, "
                "e.g. https://github.com/username"
            )

        return v


class OwnerRead(BaseOwner):
    id: int
    repositories: list["RepositoryRead"] = Field(default_factory=list)




# Repository model and schemas
class BaseRepository(SQLModel):
    name: str
    full_name: str
    url: HttpUrl
    description: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0


class Repository(BaseRepository, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="owner.id")
    owner: Owner = Relationship(back_populates="repositories")


class RepositoryCreate(SQLModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: HttpUrl) -> HttpUrl:
        parts = v.path.strip("/").split("/")

        if v.host != "github.com" or len(parts) != 2 or not all(parts):
            raise ValueError(
                "URL must point to a GitHub repository, "
                "e.g. https://github.com/owner/repo"
            )

        return v


class RepositoryRead(BaseRepository):
    id: int
    owner_username: str
