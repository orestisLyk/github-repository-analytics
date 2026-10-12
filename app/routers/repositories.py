from fastapi import APIRouter

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)

@router.get("/")
async def read_repositories():
    return {"message": "List of repositories"}