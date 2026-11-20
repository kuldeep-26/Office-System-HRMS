
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.dependencies import get_database
from app.api.dependencies.permissions import require_permission
from app.services.branch_service import BranchService
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchStatusUpdate,
)

router = APIRouter(
    prefix="/branches",
    tags=["Branch Management"]
)


def get_branch_service(db=Depends(get_database)):
    return BranchService(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_branch(
    branch_data: BranchCreate,
    current_user=Depends(require_permission("branch:create")),
    service: BranchService = Depends(get_branch_service),
):
    try:
        return await service.create_branch(
            str(current_user["organization_id"]),
            branch_data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def get_all_branches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_permission("branch:read")),
    service: BranchService = Depends(get_branch_service),
):
    return await service.get_all_branches(
        str(current_user["organization_id"]),
        skip,
        limit
    )


@router.get("/{branch_id}")
async def get_branch(
    branch_id: str,
    current_user=Depends(require_permission("branch:read")),
    service: BranchService = Depends(get_branch_service),
):
    if not ObjectId.is_valid(branch_id):
        raise HTTPException(status_code=400, detail="Invalid branch ID")

    branch = await service.get_branch(
        str(current_user["organization_id"]),
        branch_id
    )

    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    return branch


@router.put("/{branch_id}")
async def update_branch(
    branch_id: str,
    branch_data: BranchUpdate,
    current_user=Depends(require_permission("branch:update")),
    service: BranchService = Depends(get_branch_service),
):
    if not ObjectId.is_valid(branch_id):
        raise HTTPException(status_code=400, detail="Invalid branch ID")

    try:
        branch = await service.update_branch(
            str(current_user["organization_id"]),
            branch_id,
            branch_data.model_dump(exclude_unset=True)
        )

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found"
            )

        return branch

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{branch_id}/status")
async def update_branch_status(
    branch_id: str,
    status_data: BranchStatusUpdate,
    current_user=Depends(require_permission("branch:update")),
    service: BranchService = Depends(get_branch_service),
):
    if not ObjectId.is_valid(branch_id):
        raise HTTPException(status_code=400, detail="Invalid branch ID")

    branch = await service.update_branch_status(
        str(current_user["organization_id"]),
        branch_id,
        status_data.status
    )

    if not branch:
        raise HTTPException(
            status_code=404,
            detail="Branch not found"
        )

    return branch
