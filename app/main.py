from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import SessionDep, engine
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
