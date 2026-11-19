
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError

from app.db.dependencies import get_database
from app.api.dependencies.permissions import require_permission
from app.services.employee_service import EmployeeService
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeStatusUpdate,
    EmployeeResponse,
)

router = APIRouter(
    prefix="/employees",
    tags=["Employee Management"]
)


def get_employee_service(db=Depends(get_database)):
    return EmployeeService(db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user=Depends(require_permission("employee:create")),
    service: EmployeeService = Depends(get_employee_service),
):
    try:
        return await service.create_employee(
            str(current_user["organization_id"]),
            employee_data.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def get_all_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(require_permission("employee:read")),
    service: EmployeeService = Depends(get_employee_service),
):
    return await service.get_all_employees(
        str(current_user["organization_id"]),
        skip,
        limit
    )


@router.get("/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user=Depends(require_permission("employee:read")),
    service: EmployeeService = Depends(get_employee_service),
):
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    employee = await service.get_employee(
        str(current_user["organization_id"]),
        employee_id
    )

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return employee


@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    current_user=Depends(require_permission("employee:update")),
    service: EmployeeService = Depends(get_employee_service),
):
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    try:
        employee = await service.update_employee(
            str(current_user["organization_id"]),
            employee_id,
            employee_data.model_dump(exclude_unset=True)
        )

        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        return employee

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{employee_id}/status")
async def update_employee_status(
    employee_id: str,
    status_data: EmployeeStatusUpdate,
    current_user=Depends(require_permission("employee:update")),
    service: EmployeeService = Depends(get_employee_service),
):
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=400, detail="Invalid employee ID")

    employee = await service.update_employee_status(
        str(current_user["organization_id"]),
        employee_id,
        status_data.status
    )

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return employee
