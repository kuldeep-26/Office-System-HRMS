
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status
)
import logging
from datetime import timezone

from app.db.dependencies import get_database
from app.api.dependencies.permissions import require_permission
from app.schemas.attendance import (
    AttendanceActionCreate,
    AttendanceResponse
)
from app.services.attendance_service import AttendanceService

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Management"]
)

def format_utc_datetime(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")

# --------------------------------------------------
# ATTENDANCE SERVICE DEPENDENCY
# --------------------------------------------------

def get_attendance_service(
    request: Request,
    db=Depends(get_database)
):
    return AttendanceService(
        db=db,
        mongo_client=request.app.state.mongo_client
    )


# --------------------------------------------------
# RESPONSE SERIALIZER
# --------------------------------------------------

def serialize_attendance(record: dict):
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attendance record could not be retrieved"
        )

    response = {
        "id": str(record["_id"]),
        "organization_id": str(record["organization_id"]),
        "employee_id": str(record["employee_id"]),
        "session_id": record["session_id"],
        "event_type": record["event_type"],
        "event_time": format_utc_datetime(record["event_time"]),
        "source": record["source"],
        "created_at": format_utc_datetime(record["created_at"])
    }

    return AttendanceResponse(**response)


# --------------------------------------------------
# SERVICE ERROR HANDLER
# --------------------------------------------------

def handle_attendance_error(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc)
        )

    if isinstance(exc, ValueError):
        message = str(exc)

        conflict_messages = (
            "already have an open attendance session",
            "no open attendance session found",
            "idempotency key has already been used",
            "conflicted with another request",
            "unable to close the attendance session",
        )

        if any(
            item in message.lower()
            for item in conflict_messages
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


# --------------------------------------------------
# EMPLOYEE CHECK-IN
# --------------------------------------------------

@router.post(
    "/check-in",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED
)
async def employee_check_in(
    attendance_data: AttendanceActionCreate,
    current_user=Depends(
        require_permission("attendance:self_service")
    ),
    service: AttendanceService = Depends(
        get_attendance_service
    )
):
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee"
        )

    try:
        attendance = await service.check_in(
            organization_id=str(current_user["organization_id"]),
            employee_id=employee_id,
            current_user=current_user,
            idempotency_key=attendance_data.idempotency_key
        )

        return serialize_attendance(attendance)

    except (ValueError, PermissionError) as exc:
        handle_attendance_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error while processing attendance request"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing attendance"
        )


# --------------------------------------------------
# EMPLOYEE CHECK-OUT
# --------------------------------------------------

@router.post(
    "/check-out",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED
)
async def employee_check_out(
    attendance_data: AttendanceActionCreate,
    current_user=Depends(
        require_permission("attendance:self_service")
    ),
    service: AttendanceService = Depends(
        get_attendance_service
    )
):
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee"
        )

    try:
        attendance = await service.check_out(
            organization_id=str(current_user["organization_id"]),
            employee_id=employee_id,
            current_user=current_user,
            idempotency_key=attendance_data.idempotency_key
        )

        return serialize_attendance(attendance)

    except (ValueError, PermissionError) as exc:
        handle_attendance_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error while processing attendance request"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing attendance"
        )


# --------------------------------------------------
# EMPLOYEE OWN ATTENDANCE HISTORY
# --------------------------------------------------

@router.get(
    "/my-history",
    response_model=list[AttendanceResponse]
)
async def get_my_attendance_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(
        require_permission("attendance:read")
    ),
    service: AttendanceService = Depends(
        get_attendance_service
    )
):
    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee"
        )

    try:
        records = await service.get_employee_attendance(
            organization_id=str(current_user["organization_id"]),
            employee_id=employee_id,
            current_user=current_user,
            skip=skip,
            limit=limit
        )

        return [
            serialize_attendance(record)
            for record in records
        ]

    except (ValueError, PermissionError) as exc:
        handle_attendance_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error while processing attendance request"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing attendance"
        )


# --------------------------------------------------
# ORGANIZATION ATTENDANCE HISTORY
# --------------------------------------------------

@router.get(
    "/organization",
    response_model=list[AttendanceResponse]
)
async def get_organization_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(
        require_permission("attendance:organization_read")
    ),
    service: AttendanceService = Depends(
        get_attendance_service
    )
):
    try:
        records = await service.get_organization_attendance(
            organization_id=str(current_user["organization_id"]),
            skip=skip,
            limit=limit
        )

        return [
            serialize_attendance(record)
            for record in records
        ]

    except (ValueError, PermissionError) as exc:
        handle_attendance_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error while processing attendance request"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing attendance"
        )
