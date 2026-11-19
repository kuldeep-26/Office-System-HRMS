
from fastapi import APIRouter, Depends

from app.api.dependencies.permissions import require_permission


router = APIRouter(
    prefix="/rbac-test",
    tags=["RBAC Testing"]
)


@router.get(
    "/employee-read",
    dependencies=[
        Depends(require_permission("employee:read"))
    ]
)
async def test_employee_read():

    return {
        "message": "Employee read permission granted"
    }


@router.post(
    "/employee-create",
    dependencies=[
        Depends(require_permission("employee:create"))
    ]
)
async def test_employee_create():

    return {
        "message": "Employee create permission granted"
    }
