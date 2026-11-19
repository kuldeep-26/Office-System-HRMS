
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.dependencies import get_database
from app.api.dependencies.permissions import require_permission
from app.services.designation_service import DesignationService
from app.schemas.designation import (
    DesignationCreate,
    DesignationUpdate,
    DesignationStatusUpdate,
)

router = APIRouter(
    prefix="/designations",
    tags=["Designation Management"]
)


def get_designation_service(db=Depends(get_database)):
    return DesignationService(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_designation(
    designation_data: DesignationCreate,
    current_user=Depends(require_permission("designation:create")),
    service: DesignationService = Depends(get_designation_service),
):
    try:
        return await service.create_designation(
            str(current_user["organization_id"]),
            designation_data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def get_all_designations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_permission("designation:read")),
    service: DesignationService = Depends(get_designation_service),
):
    return await service.get_all_designations(
        str(current_user["organization_id"]),
        skip,
        limit
    )


@router.get("/{designation_id}")
async def get_designation(
    designation_id: str,
    current_user=Depends(require_permission("designation:read")),
    service: DesignationService = Depends(get_designation_service),
):
    if not ObjectId.is_valid(designation_id):
        raise HTTPException(status_code=400, detail="Invalid designation ID")

    designation = await service.get_designation(
        str(current_user["organization_id"]),
        designation_id
    )

    if not designation:
        raise HTTPException(status_code=404, detail="Designation not found")

    return designation


@router.put("/{designation_id}")
async def update_designation(
    designation_id: str,
    designation_data: DesignationUpdate,
    current_user=Depends(require_permission("designation:update")),
    service: DesignationService = Depends(get_designation_service),
):
    if not ObjectId.is_valid(designation_id):
        raise HTTPException(status_code=400, detail="Invalid designation ID")

    try:
        designation = await service.update_designation(
            str(current_user["organization_id"]),
            designation_id,
            designation_data.model_dump(exclude_unset=True)
        )

        if not designation:
            raise HTTPException(
                status_code=404,
                detail="Designation not found"
            )

        return designation

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{designation_id}/status")
async def update_designation_status(
    designation_id: str,
    status_data: DesignationStatusUpdate,
    current_user=Depends(require_permission("designation:update")),
    service: DesignationService = Depends(get_designation_service),
):
    if not ObjectId.is_valid(designation_id):
        raise HTTPException(status_code=400, detail="Invalid designation ID")

    designation = await service.update_designation_status(
        str(current_user["organization_id"]),
        designation_id,
        status_data.status
    )

    if not designation:
        raise HTTPException(
            status_code=404,
            detail="Designation not found"
        )

    return designation
