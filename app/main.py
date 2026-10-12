from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine
from app.routers.analytics import router as analytics_router
from app.routers.jobs import router as jobs_router
from app.routers.owners import router as owners_router
from app.routers.repositories import router as repositories_router
from sqlmodel import SQLModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code here
    SQLModel.metadata.create_all(engine)
    print("Database ready")
    yield
    # Shutdown code here
    print("Shutting down")


app = FastAPI(
    title="GitHub Repository Analytics",
    description="An API for analyzing GitHub repositories.",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(owners_router)
app.include_router(repositories_router)
app.include_router(jobs_router)
app.include_router(analytics_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "GitHub Repository Analytics API"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
