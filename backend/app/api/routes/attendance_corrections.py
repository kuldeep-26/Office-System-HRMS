
import logging
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    Request
)

from app.api.dependencies.permissions import require_permission

from app.schemas.attendance_correction import (
    AttendanceCorrectionCreate,
    AttendanceCorrectionReview,
    AttendanceCorrectionResponse
)

from app.services.attendance_correction_service import (
    AttendanceCorrectionService
)

from app.db.dependencies import get_database


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/attendance/corrections",
    tags=["Attendance Corrections"]
)


# --------------------------------------------------
# SERVICE DEPENDENCY
# --------------------------------------------------

def get_attendance_correction_service(
    request: Request,
    db=Depends(get_database)
):
    return AttendanceCorrectionService(
        db,
        request.app.state.mongo_client
    )

# --------------------------------------------------
# UTC FORMATTER
# --------------------------------------------------

def format_utc_datetime(value):

    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(
            value,
            datetime.min.time(),
            tzinfo=timezone.utc
        )

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


# --------------------------------------------------
# RESPONSE SERIALIZER
# --------------------------------------------------

def serialize_correction(correction):

    if not correction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attendance correction could not be retrieved"
        )

    attendance_date = correction["attendance_date"]

    if isinstance(attendance_date, datetime):
        attendance_date = attendance_date.date()

    response = {
        "id": str(correction["_id"]),
        "organization_id": str(correction["organization_id"]),
        "employee_id": str(correction["employee_id"]),
        "correction_type": correction["correction_type"],
        "attendance_date": attendance_date.isoformat(),
        "original_event_id": (
            str(correction["original_event_id"])
            if correction.get("original_event_id")
            else None
        ),
        "proposed_event_time": format_utc_datetime(
            correction["proposed_event_time"]
        ),
        "reason": correction["reason"],
        "status": correction["status"],
        "created_by_user_id": str(
            correction["created_by_user_id"]
        ),
        "reviewed_by_user_id": (
            str(correction["reviewed_by_user_id"])
            if correction.get("reviewed_by_user_id")
            else None
        ),
        "reviewed_at": format_utc_datetime(
            correction.get("reviewed_at")
        ),
        "review_reason": correction.get("review_reason"),
        "applied_at": format_utc_datetime(
            correction.get("applied_at")
        ),
        "applied_event_id": (
            str(correction["applied_event_id"])
            if correction.get("applied_event_id")
            else None
        ),
        "created_at": format_utc_datetime(
            correction["created_at"]
        ),
        "updated_at": format_utc_datetime(
            correction["updated_at"]
        )
    }

    return AttendanceCorrectionResponse(**response)


# --------------------------------------------------
# ERROR HANDLER
# --------------------------------------------------

def handle_correction_error(exc: Exception):

    if isinstance(exc, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc)
        )

    if isinstance(exc, ValueError):

        message = str(exc)

        if "not found" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message
            )

        if (
            "only pending" in message.lower()
            or "already" in message.lower()
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
# CREATE CORRECTION REQUEST
# --------------------------------------------------

@router.post(
    "",
    response_model=AttendanceCorrectionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_attendance_correction(
    correction_data: AttendanceCorrectionCreate,
    current_user=Depends(
        require_permission("attendance:correction_create")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee"
        )

    try:
        correction = await service.create_correction(
            organization_id=str(current_user["organization_id"]),
            employee_id=employee_id,
            current_user=current_user,
            correction_data=correction_data
        )

        return serialize_correction(correction)

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error creating attendance correction"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating attendance correction"
        )


# --------------------------------------------------
# GET EMPLOYEE CORRECTION REQUESTS
# --------------------------------------------------

@router.get(
    "/my-requests",
    response_model=list[AttendanceCorrectionResponse]
)
async def get_my_attendance_corrections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(
        require_permission("attendance:correction_read")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    employee_id = current_user.get("employee_id")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not linked to an employee"
        )

    try:
        corrections = await service.get_employee_corrections(
            organization_id=str(current_user["organization_id"]),
            employee_id=employee_id,
            current_user=current_user,
            skip=skip,
            limit=limit
        )

        return [
            serialize_correction(correction)
            for correction in corrections
        ]

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error retrieving employee attendance corrections"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving attendance corrections"
        )


# --------------------------------------------------
# GET ORGANIZATION CORRECTION REQUESTS
# --------------------------------------------------

@router.get(
    "",
    response_model=list[AttendanceCorrectionResponse]
)
async def get_organization_attendance_corrections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    correction_status: Literal[
        "pending",
        "approved",
        "rejected",
        "applied"
    ] | None = Query(None, alias="status"),
    current_user=Depends(
        require_permission("attendance:correction_read")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    try:
        corrections = await service.get_organization_corrections(
            organization_id=str(current_user["organization_id"]),
            current_user=current_user,
            skip=skip,
            limit=limit,
            status=correction_status
        )

        return [
            serialize_correction(correction)
            for correction in corrections
        ]

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error retrieving organization attendance corrections"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving attendance corrections"
        )


# --------------------------------------------------
# GET CORRECTION BY ID
# --------------------------------------------------

@router.get(
    "/{correction_id}",
    response_model=AttendanceCorrectionResponse
)
async def get_attendance_correction(
    correction_id: str,
    current_user=Depends(
        require_permission("attendance:correction_read")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    try:
        correction = await service.get_correction_by_id(
            organization_id=str(current_user["organization_id"]),
            correction_id=correction_id,
            current_user=current_user
        )

        return serialize_correction(correction)

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error retrieving attendance correction"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving attendance correction"
        )


# --------------------------------------------------
# APPROVE CORRECTION
# --------------------------------------------------

@router.post(
    "/{correction_id}/approve",
    response_model=AttendanceCorrectionResponse
)
async def approve_attendance_correction(
    correction_id: str,
    review_data: AttendanceCorrectionReview,
    current_user=Depends(
        require_permission("attendance:correction_review")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    try:
        correction = await service.approve_correction(
            organization_id=str(current_user["organization_id"]),
            correction_id=correction_id,
            current_user=current_user,
            review_reason=review_data.review_reason
        )

        if correction is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Correction was already reviewed or modified"
            )

        return serialize_correction(correction)

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error approving attendance correction"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while approving attendance correction"
        )


# --------------------------------------------------
# REJECT CORRECTION
# --------------------------------------------------

@router.post(
    "/{correction_id}/reject",
    response_model=AttendanceCorrectionResponse
)
async def reject_attendance_correction(
    correction_id: str,
    review_data: AttendanceCorrectionReview,
    current_user=Depends(
        require_permission("attendance:correction_review")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):

    try:
        correction = await service.reject_correction(
            organization_id=str(current_user["organization_id"]),
            correction_id=correction_id,
            current_user=current_user,
            review_reason=review_data.review_reason
        )

        if correction is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Correction was already reviewed or modified"
            )

        return serialize_correction(correction)

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error rejecting attendance correction"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while rejecting attendance correction"
        )


# --------------------------------------------------
# APPLY APPROVED CORRECTION
# --------------------------------------------------

@router.post(
    "/{correction_id}/apply",
    response_model=AttendanceCorrectionResponse
)
async def apply_attendance_correction(
    correction_id: str,
    current_user=Depends(
        require_permission("attendance:correction_review")
    ),
    service: AttendanceCorrectionService = Depends(
        get_attendance_correction_service
    )
):
    try:
        correction = await service.apply_correction(
            organization_id=str(current_user["organization_id"]),
            correction_id=correction_id,
            current_user=current_user
        )

        return serialize_correction(correction)

    except (ValueError, PermissionError) as exc:
        handle_correction_error(exc)

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected error applying attendance correction"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An unexpected error occurred while applying "
                "attendance correction"
            )
        )
