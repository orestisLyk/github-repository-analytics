from fastapi import APIRouter

router = APIRouter(
    prefix="/owners",
    tags=["Owners"],
)

@router.get("/")
async def read_owners():
    return {"message": "List of owners"}