from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Relationship, SQLModel, Field
from pydantic import HttpUrl, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# Owner model and schemas
class BaseOwner(SQLModel):
    username: str
    url: str


class Owner(BaseOwner, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
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
    url: str
    description: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0


class Repository(BaseRepository, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(unique=True, index=True)
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


class IngestionJob(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    kind: str = Field(index=True)
    target: str
    status: str = Field(default="pending", index=True)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class IngestionJobRead(SQLModel):
    id: str
    kind: str
    target: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class OwnerAnalyticsSummary(SQLModel):
    owner_username: str
    repository_count: int
    total_stars: int
    total_forks: int
    total_open_issues: int
    average_stars: float
    median_stars: float
    average_forks: float
    issue_pressure: float
    health_score: float


class RepositoryLeaderboardItem(SQLModel):
    full_name: str
    owner_username: str
    stars: int
    forks: int
    open_issues: int
    popularity_score: int
    issue_pressure: float


class OwnerComparison(SQLModel):
    left: OwnerAnalyticsSummary
    right: OwnerAnalyticsSummary
    winner_by_total_stars: str
    winner_by_health_score: str
