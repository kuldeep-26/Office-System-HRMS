import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.repositories.face_enrollment_repository import (
    FaceEnrollmentRepository
)

from app.core.face_storage import (
    save_face_photo,
    delete_face_photo,
    get_face_photo
)


logger = logging.getLogger(__name__)

class FaceEnrollmentService:

    def __init__(self, db):
        self.db = db
        self.repository = FaceEnrollmentRepository(db)

    # VALIDATE ORGANIZATION
    async def _validate_organization(self, organization_id):

        if not ObjectId.is_valid(organization_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID"
            )

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise HTTPException(
                status_code=404,
                detail="Organization not found or inactive"
            )

    # VALIDATE EMPLOYEE
    async def _validate_employee(
        self,
        organization_id,
        employee_id
    ):

        if not ObjectId.is_valid(employee_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid employee ID"
            )

        employee = await self.db.employees.find_one({
            "_id": ObjectId(employee_id),
            "organization_id": ObjectId(organization_id),
            "status": "active"
        })

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Active employee not found in this organization"
            )

        return employee

    # SERIALIZE ENROLLMENT
    @staticmethod
    def _serialize(enrollment):

        if not enrollment:
            return None

        for field in (
            "_id",
            "organization_id",
            "employee_id",
            "consented_by"
        ):
            if enrollment.get(field) is not None:
                enrollment[field] = str(enrollment[field])

        enrollment["id"] = str(enrollment.pop("_id"))

        for field in (
            "created_at",
            "updated_at",
            "consent_at",
            "revoked_at"
        ):
            value = enrollment.get(field)

            if isinstance(value, datetime):
                enrollment[field] = value.isoformat()

        return enrollment

    # RECORD EMPLOYEE CONSENT
    async def record_consent(
        self,
        organization_id,
        employee_id,
        current_user_id,
        consent_data
    ):

        await self._validate_organization(organization_id)

        await self._validate_employee(
            organization_id,
            employee_id
        )

        # Only the employee can provide their own consent
        if not ObjectId.is_valid(current_user_id):
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID"
            )

        user = await self.db.users.find_one({
            "_id": ObjectId(current_user_id),
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id),
            "status": "active"
        })

        if not user:
            raise HTTPException(
                status_code=403,
                detail="Only the linked employee can provide consent"
            )

        if consent_data.get("consent_given") is not True:
            raise HTTPException(
                status_code=400,
                detail="Explicit consent is required for face enrollment"
            )

        
        # Check existing enrollment record
        existing = await self.repository.get_by_employee(
            organization_id,
            employee_id
        )

        if existing:

            # Do not allow duplicate active consent
            if existing.get("consent_given") is True:
                raise HTTPException(
                    status_code=409,
                    detail="Active face enrollment consent already exists"
                )

            # Allow consent renewal only after revocation
            if existing.get("enrollment_status") != "revoked":
                raise HTTPException(
                    status_code=409,
                    detail="Existing enrollment cannot be renewed"
                )

            renewed_enrollment = await self.repository.renew_consent(
                organization_id=organization_id,
                enrollment_id=str(existing["_id"]),
                consent_data={
                    "consent_version": consent_data["consent_version"],
                    "consented_by": current_user_id,
                    "purpose": consent_data.get(
                        "purpose",
                        "attendance_verification"
                    )
                }
            )

            if not renewed_enrollment:
                raise HTTPException(
                    status_code=409,
                    detail="Unable to renew face enrollment consent"
                )

            return self._serialize(renewed_enrollment)


        now = datetime.now(timezone.utc)

        enrollment_data = {
            "organization_id": organization_id,
            "employee_id": employee_id,
            "consented_by": current_user_id,
            "consent_given": True,
            "consent_version": consent_data["consent_version"],
            "purpose": consent_data.get(
                "purpose",
                "attendance_verification"
            ),
            "consent_at": now,
            "enrollment_status": "consented",
            "consent_history": [
                {
                    "action": "consented",
                    "consent_version": consent_data["consent_version"],
                    "consented_by": ObjectId(current_user_id),
                    "consent_at": now,
                    "purpose": consent_data.get(
                        "purpose",
                        "attendance_verification"
                    )
                }
            ],
        }

        enrollment = await self.repository.create(
            enrollment_data
        )

        return self._serialize(enrollment)

    
    # UPLOAD EMPLOYEE FACE PHOTO
    async def upload_face_photo(
        self,
        organization_id,
        employee_id,
        current_user_id,
        file
    ):

        # Validate organization
        await self._validate_organization(organization_id)

        # Validate employee
        await self._validate_employee(
            organization_id,
            employee_id
        )

        # Validate logged-in user
        if not ObjectId.is_valid(current_user_id):
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID"
            )

        user = await self.db.users.find_one({
            "_id": ObjectId(current_user_id),
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id),
            "status": "active"
        })

        if not user:
            raise HTTPException(
                status_code=403,
                detail="Only the linked employee can upload their face photo"
            )

        # Check existing consent
        enrollment = await self.repository.get_by_employee(
            organization_id,
            employee_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=404,
                detail="Face enrollment consent record not found"
            )

        if (
            enrollment.get("consent_given") is not True
            or enrollment.get("enrollment_status") != "consented"
        ):
            raise HTTPException(
                status_code=403,
                detail="Valid face enrollment consent is required"
            )

        if enrollment.get("stored_filename"):
            raise HTTPException(
                status_code=409,
                detail="A face photo has already been uploaded"
            )

        # Save encrypted photo
        photo_data = await save_face_photo(file)

        stored_filename = photo_data["stored_filename"]

        try:
            # Attach photo metadata to enrollment
            updated_enrollment = await self.repository.attach_photo(
                organization_id=organization_id,
                enrollment_id=str(enrollment["_id"]),
                photo_data={
                    "stored_filename": stored_filename,
                    "content_type": photo_data["content_type"],
                    "file_size": photo_data["file_size"]
                }
            )

            if not updated_enrollment:
                raise HTTPException(
                    status_code=409,
                    detail="Face enrollment record could not be updated"
                )

            return self._serialize(updated_enrollment)

        except Exception:
            # Remove encrypted file if database update fails
            try:
                delete_face_photo(stored_filename)

            except Exception:
                logger.exception(
                    "Failed to clean up encrypted face photo "
                    "after enrollment update failure"
                )

            raise

    
    # REVOKE EMPLOYEE FACE ENROLLMENT CONSENT
    async def revoke_consent(
        self,
        organization_id,
        employee_id,
        current_user_id
    ):

        # Validate organization
        await self._validate_organization(organization_id)

        # Validate employee
        await self._validate_employee(
            organization_id,
            employee_id
        )

        # Validate logged-in user
        if not ObjectId.is_valid(current_user_id):
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID"
            )

        # Only the linked employee can revoke consent
        user = await self.db.users.find_one({
            "_id": ObjectId(current_user_id),
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id),
            "status": "active"
        })

        if not user:
            raise HTTPException(
                status_code=403,
                detail="Only the linked employee can revoke their consent"
            )

        # Find enrollment record
        enrollment = await self.repository.get_by_employee(
            organization_id,
            employee_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=404,
                detail="Face enrollment record not found"
            )

        if enrollment.get("consent_given") is not True:
            raise HTTPException(
                status_code=409,
                detail="Face enrollment consent has already been revoked"
            )

        # Revoke consent in database
        result = await self.repository.revoke_consent(
            organization_id=organization_id,
            enrollment_id=str(enrollment["_id"])
        )

        if not result:
            raise HTTPException(
                status_code=409,
                detail="Unable to revoke face enrollment consent"
            )

        # Delete encrypted photo if one exists
        stored_filename = result.get("stored_filename")

        if stored_filename:
            try:
                delete_face_photo(stored_filename)

            except HTTPException as exc:
                if exc.status_code != 404:
                    logger.exception(
                        "Face photo cleanup failed after consent revocation"
                    )

                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "Consent was revoked, but photo cleanup failed. "
                            "Cleanup is pending administrator action."
                        )
                    )

            except Exception:
                logger.exception(
                    "Unexpected error during face photo cleanup"
                )

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Consent was revoked, but photo cleanup failed. "
                        "Cleanup is pending administrator action."
                    )
                )

            # Clear the pending cleanup marker after successful deletion
            marker_cleared = await self.repository.clear_photo_cleanup_marker(
                organization_id=organization_id,
                enrollment_id=str(enrollment["_id"])
            )

            if not marker_cleared:
                logger.warning(
                    "Face photo cleanup marker could not be cleared for "
                    "enrollment ID: %s",
                    enrollment["_id"]
                )

        return self._serialize(result["enrollment"])

    
    # RETRIEVE EMPLOYEE FACE PHOTO
    async def retrieve_face_photo(
        self,
        organization_id,
        employee_id,
        current_user_id
    ):

        # Validate organization
        await self._validate_organization(organization_id)

        # Validate employee
        await self._validate_employee(
            organization_id,
            employee_id
        )

        # Validate logged-in user
        if not ObjectId.is_valid(current_user_id):
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID"
            )

        # Only the linked employee can retrieve their photo
        user = await self.db.users.find_one({
            "_id": ObjectId(current_user_id),
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id),
            "status": "active"
        })

        if not user:
            raise HTTPException(
                status_code=403,
                detail="Only the linked employee can access their face photo"
            )

        # Find enrollment
        enrollment = await self.repository.get_by_employee(
            organization_id,
            employee_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=404,
                detail="Face enrollment record not found"
            )

        # Verify active consent
        if (
            enrollment.get("consent_given") is not True
            or enrollment.get("enrollment_status") != "photo_uploaded"
        ):
            raise HTTPException(
                status_code=403,
                detail="Active face enrollment consent is required"
            )

        stored_filename = enrollment.get("stored_filename")

        if not stored_filename:
            raise HTTPException(
                status_code=404,
                detail="Face photo not found"
            )

        # Decrypt photo in memory
        image_content = get_face_photo(stored_filename)

        return image_content

    
    # LIST ORGANIZATION FACE ENROLLMENTS
    async def list_organization_enrollments(
        self,
        organization_id,
        enrollment_status=None,
        skip=0,
        limit=50
    ):

        # Validate organization
        await self._validate_organization(organization_id)

        # Validate pagination
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip cannot be negative"
            )

        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )

        # Validate enrollment status
        allowed_statuses = {
            "consent_pending",
            "consented",
            "photo_uploaded",
            "enrolled",
            "rejected",
            "revoked"
        }

        if (
            enrollment_status is not None
            and enrollment_status not in allowed_statuses
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid enrollment status"
            )

        # Retrieve organization-scoped records
        enrollments = await self.repository.get_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            enrollment_status=enrollment_status
        )

        return [
            self._serialize(enrollment)
            for enrollment in enrollments
        ]

