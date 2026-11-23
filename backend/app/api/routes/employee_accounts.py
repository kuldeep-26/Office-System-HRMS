
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.db.dependencies import get_database
from app.schemas.employee_account import (
    EmployeeAccountCreate,
    EmployeeAccountResponse
)
from app.services.employee_account_service import EmployeeAccountService
from app.api.dependencies.permissions import require_permission


router = APIRouter(
    prefix="/employee-accounts",
    tags=["Employee Accounts"]
)


@router.post(
    "/{employee_id}",
    response_model=EmployeeAccountResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_employee_account(
    employee_id: str,
    account_data: EmployeeAccountCreate,
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("employee:create")
    )
):

    # Only organization HR/Admin roles can create employee accounts
    allowed_roles = {"org_admin", "hr_manager"}

    if not allowed_roles.intersection(
        set(current_user.get("role_names", []))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR/Admin users can create employee accounts"
        )

    service = EmployeeAccountService(db)

    try:
        return await service.create_employee_account(
            organization_id=current_user["organization_id"],
            employee_id=employee_id,
            account_data=account_data.model_dump()
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
