# GitHub Repository Analytics

FastAPI backend for collecting and analyzing GitHub owner and repository data, including ingestion jobs, leaderboard views, and owner comparison metrics.

## Features

- Owner ingestion from GitHub URLs
- Repository ingestion and refresh workflows
- Background job tracking for ingestion status
- Analytics endpoints for owner summaries and repository leaderboards
- PostgreSQL persistence with SQLModel
- Docker Compose support for local development

## Tech Stack

- Python
- FastAPI
- SQLModel / SQLAlchemy
- PostgreSQL
- Uvicorn
- Pytest

## Project Structure

```text
app/
  dao/
  routers/
  services/
  database.py
  main.py
  models.py
tests/
docker-compose.yml
requirements.txt
```

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Python 3.11+ (for local non-Docker runs)

## Environment Variables

The app expects these variables:

| Name | Description |
| --- | --- |
| DB_USERNAME | Database username |
| DB_PASSWORD | Database password |
| DB_HOST | Database host |
| DB_PORT | Database port |
| DB_NAME | Database name |
| DEBUG | SQLAlchemy echo logging toggle (`True` or `False`) |

Setup recommendation:

1. Copy `.env.example` to `.env`.
2. Set your local credentials in `.env`.
3. Keep `DEBUG=False` unless you are actively debugging SQL statements.

Security note:
- `.env` is gitignored. Do not commit real credentials.

## Run with Docker Compose

1. Start Docker Desktop.
2. From the project root, run:

```bash
docker compose up --build
```

3. Open the API:
- App root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

Notes:
- In Compose, the app uses `DB_HOST=postgres` so containers can communicate over the internal network.
- The database is persisted in the `postgres_data` volume.
- Compose now defaults `DEBUG` to `False` when not explicitly set.

To stop services:

```bash
docker compose down
```

## Makefile Shortcuts

If you use GNU Make, common commands are available:

```bash
make up
make ps
make logs
make health
make test
make down
```

## Run Locally (Without Docker)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure `.env` contains valid local database settings.
4. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Tests

Run endpoint tests:

```bash
pytest -q
```

## API Endpoints

### Core

- `GET /` - Basic API message
- `GET /health` - Liveness check

### Owners

- `GET /owners/` - List owners (pagination and username filter)
- `POST /owners/` - Create owner and ingest repositories
- `POST /owners/ingest` - Queue owner ingestion job
- `POST /owners/{owner_username}/refresh` - Refresh owner and repositories

### Repositories

- `GET /repositories/` - List repositories (filters and sorting)
- `POST /repositories/` - Create repository by GitHub URL
- `POST /repositories/{owner_username}/{repository_name}/refresh` - Refresh repository stats

### Jobs

- `GET /jobs/{job_id}` - Get ingestion job status

### Analytics

- `GET /analytics/owners/{owner_username}/summary` - Owner summary metrics
- `GET /analytics/repositories/leaderboard` - Repository leaderboard by metric
- `GET /analytics/owners/compare?left=<owner>&right=<owner>` - Compare two owners

## Metric Definitions

This project uses pragmatic scoring heuristics for ranking and comparison.

- `popularity_score = stars + 2 * forks`
- `issue_pressure = open_items / max(total_stars, 1)`
- `engagement_score = clamp(0, 100, 50 + average_stars * 0.2 - issue_pressure * 25)`

Notes:
- `open_items` comes from GitHub `open_issues_count`, which includes open pull requests.
- `engagement_score` is an internal comparative signal, not an official GitHub health metric.

## Next Improvements

- Add CI checks for linting and tests
- Add migrations support via Alembic workflows
- Add authentication and rate limiting for production exposure