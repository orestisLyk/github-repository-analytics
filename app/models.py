
from sqlmodel import SQLModel, Field
from pydantic import HttpUrl, field_validator


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