from fastapi import APIRouter, status

from app.database import SessionDep
from app.models import OwnerCreate, OwnerRead
from app.services.owners import create_owner as create_owner_service
from app.services.owners import list_owners as list_owners_service

router = APIRouter(
    prefix="/owners",
    tags=["Owners"],
)

@router.get("/", response_model=list[OwnerRead])
async def read_owners(session: SessionDep) -> list[OwnerRead]:
    return list_owners_service(session)


@router.post("/", response_model=OwnerRead, status_code=status.HTTP_201_CREATED)
async def create_owner(owner_create: OwnerCreate, session: SessionDep) -> OwnerRead:
    return await create_owner_service(owner_create, session)