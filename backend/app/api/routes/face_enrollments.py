
from fastapi import (
    APIRouter,
    Depends,
    status,
    File,
    UploadFile,
    Response
)

from app.db.dependencies import get_database
from app.api.dependencies.permissions import (
    get_current_organization_user,
    require_permission
)
from app.schemas.face_enrollment import (
    FaceEnrollmentConsentCreate,
    FaceEnrollmentResponse
)
from app.services.face_enrollment_service import (
    FaceEnrollmentService
)


router = APIRouter(
    prefix="/face-enrollments",
    tags=["Face Enrollment"]
)

NO_STORE_HEADERS = {
    "Cache-Control": "no-store, private",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff"
}


# --------------------------------------------------
# RECORD EMPLOYEE FACE ENROLLMENT CONSENT
# --------------------------------------------------

@router.post(
    "/{employee_id}/consent",
    response_model=FaceEnrollmentResponse,
    status_code=status.HTTP_201_CREATED
)
async def record_face_enrollment_consent(
    employee_id: str,
    consent_data: FaceEnrollmentConsentCreate,
    response: Response,
    db=Depends(get_database),
    current_user: dict = Depends(
        get_current_organization_user
    )
):

    response.headers.update(NO_STORE_HEADERS)
    
    service = FaceEnrollmentService(db)

    return await service.record_consent(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        current_user_id=current_user["id"],
        consent_data=consent_data.model_dump()
    )



# --------------------------------------------------
# UPLOAD EMPLOYEE FACE PHOTO
# --------------------------------------------------

@router.post(
    "/{employee_id}/photo",
    response_model=FaceEnrollmentResponse,
    status_code=status.HTTP_200_OK
)
async def upload_employee_face_photo(
    employee_id: str,
    response: Response,
    file: UploadFile = File(...),
    db=Depends(get_database),
    current_user: dict = Depends(
        get_current_organization_user
    )
):

    response.headers.update(NO_STORE_HEADERS)

    service = FaceEnrollmentService(db)

    return await service.upload_face_photo(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        current_user_id=current_user["id"],
        file=file
    )


# --------------------------------------------------
# REVOKE EMPLOYEE FACE ENROLLMENT CONSENT
# --------------------------------------------------

@router.delete(
    "/{employee_id}/consent",
    response_model=FaceEnrollmentResponse,
    status_code=status.HTTP_200_OK
)
async def revoke_face_enrollment_consent(
    employee_id: str,
    response: Response,
    db=Depends(get_database),
    current_user: dict = Depends(
        get_current_organization_user
    )
):

    response.headers.update(NO_STORE_HEADERS)

    service = FaceEnrollmentService(db)

    return await service.revoke_consent(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        current_user_id=current_user["id"]
    )



# --------------------------------------------------
# RETRIEVE EMPLOYEE FACE PHOTO
# --------------------------------------------------

@router.get(
    "/{employee_id}/photo",
    response_class=Response
)
async def retrieve_employee_face_photo(
    employee_id: str,
    db=Depends(get_database),
    current_user: dict = Depends(
        get_current_organization_user
    )
):

    service = FaceEnrollmentService(db)

    image_content = await service.retrieve_face_photo(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        current_user_id=current_user["id"]
    )

    return Response(
        content=image_content,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff"
        }
    )




# --------------------------------------------------
# LIST ORGANIZATION FACE ENROLLMENT STATUSES
# --------------------------------------------------

@router.get(
    "/organization/statuses",
    status_code=status.HTTP_200_OK
)
async def list_organization_face_enrollments(
    enrollment_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("face_enrollment:read")
    )
):

    response.headers.update(NO_STORE_HEADERS)

    service = FaceEnrollmentService(db)

    return await service.list_organization_enrollments(
        organization_id=current_user["organization_id"],
        enrollment_status=enrollment_status,
        skip=skip,
        limit=limit
    )
