
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.dependencies import get_database
from app.api.dependencies.permissions import require_permission
from app.services.department_service import DepartmentService
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentStatusUpdate,
)

router = APIRouter(
    prefix="/departments",
    tags=["Department Management"]
)


def get_department_service(db=Depends(get_database)):
    return DepartmentService(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_department(
    department_data: DepartmentCreate,
    current_user=Depends(require_permission("department:create")),
    service: DepartmentService = Depends(get_department_service),
):
    try:
        return await service.create_department(
            str(current_user["organization_id"]),
            department_data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def get_all_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_permission("department:read")),
    service: DepartmentService = Depends(get_department_service),
):
    return await service.get_all_departments(
        str(current_user["organization_id"]),
        skip,
        limit
    )


@router.get("/{department_id}")
async def get_department(
    department_id: str,
    current_user=Depends(require_permission("department:read")),
    service: DepartmentService = Depends(get_department_service),
):
    if not ObjectId.is_valid(department_id):
        raise HTTPException(status_code=400, detail="Invalid department ID")

    department = await service.get_department(
        str(current_user["organization_id"]),
        department_id
    )

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    return department


@router.put("/{department_id}")
async def update_department(
    department_id: str,
    department_data: DepartmentUpdate,
    current_user=Depends(require_permission("department:update")),
    service: DepartmentService = Depends(get_department_service),
):
    if not ObjectId.is_valid(department_id):
        raise HTTPException(status_code=400, detail="Invalid department ID")

    try:
        department = await service.update_department(
            str(current_user["organization_id"]),
            department_id,
            department_data.model_dump(exclude_unset=True)
        )

        if not department:
            raise HTTPException(status_code=404, detail="Department not found")

        return department

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{department_id}/status")
async def update_department_status(
    department_id: str,
    status_data: DepartmentStatusUpdate,
    current_user=Depends(require_permission("department:update")),
    service: DepartmentService = Depends(get_department_service),
):
    if not ObjectId.is_valid(department_id):
        raise HTTPException(status_code=400, detail="Invalid department ID")

    department = await service.update_department_status(
        str(current_user["organization_id"]),
        department_id,
        status_data.status
    )

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    return department
