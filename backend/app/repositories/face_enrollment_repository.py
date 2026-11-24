
from datetime import datetime, timezone

from bson import ObjectId


class FaceEnrollmentRepository:

    def __init__(self, db):
        self.collection = db.face_enrollments

    # CREATE ENROLLMENT
    async def create(self, enrollment_data: dict):

        data = enrollment_data.copy()

        data["organization_id"] = ObjectId(
            data["organization_id"]
        )

        data["employee_id"] = ObjectId(
            data["employee_id"]
        )

        now = datetime.now(timezone.utc)

        data["created_at"] = now
        data["updated_at"] = now

        result = await self.collection.insert_one(data)

        return await self.get_by_id(
            str(data["organization_id"]),
            str(result.inserted_id)
        )

    # GET ENROLLMENT BY ID
    async def get_by_id(
        self,
        organization_id: str,
        enrollment_id: str
    ):

        if not ObjectId.is_valid(enrollment_id):
            return None

        return await self.collection.find_one({
            "_id": ObjectId(enrollment_id),
            "organization_id": ObjectId(organization_id)
        })

    # GET ENROLLMENT BY EMPLOYEE
    async def get_by_employee(
        self,
        organization_id: str,
        employee_id: str
    ):

        if not ObjectId.is_valid(employee_id):
            return None

        return await self.collection.find_one({
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id)
        })

    
    # GET ALL FACE ENROLLMENTS IN ORGANIZATION
    async def get_by_organization(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 50,
        enrollment_status: str | None = None
    ):

        if not ObjectId.is_valid(organization_id):
            return []

        query = {
            "organization_id": ObjectId(organization_id)
        }

        if enrollment_status:
            query["enrollment_status"] = enrollment_status

        cursor = (
            self.collection
            .find(
                query,
                {
                    "stored_filename": 0,
                    "consent_history": 0
                }
            )
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)


    
    # ATTACH ENCRYPTED FACE PHOTO
    async def attach_photo(
        self,
        organization_id: str,
        enrollment_id: str,
        photo_data: dict
    ):

        if not ObjectId.is_valid(organization_id):
            return None

        if not ObjectId.is_valid(enrollment_id):
            return None

        allowed_fields = {
            "stored_filename",
            "content_type",
            "file_size"
        }

        if set(photo_data.keys()) != allowed_fields:
            raise ValueError("Invalid face photo metadata")

        update_data = {
            **photo_data,
            "photo_uploaded_at": datetime.now(timezone.utc),
            "enrollment_status": "photo_uploaded",
            "updated_at": datetime.now(timezone.utc)
        }

        result = await self.collection.update_one(
            {
                "_id": ObjectId(enrollment_id),
                "organization_id": ObjectId(organization_id),
                "consent_given": True,
                "enrollment_status": "consented",
                "stored_filename": {"$exists": False}
            },
            {
                "$set": update_data
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            enrollment_id
        )

    
    # REVOKE FACE ENROLLMENT CONSENT
    async def revoke_consent(
        self,
        organization_id: str,
        enrollment_id: str
    ):

        if not ObjectId.is_valid(organization_id):
            return None

        if not ObjectId.is_valid(enrollment_id):
            return None

        # Get existing enrollment and photo filename
        existing = await self.get_by_id(
            organization_id,
            enrollment_id
        )

        if not existing:
            return None

        if existing.get("consent_given") is not True:
            return None

        stored_filename = existing.get("stored_filename")

        now = datetime.now(timezone.utc)

        update_fields = {
            "consent_given": False,
            "enrollment_status": "revoked",
            "revoked_at": now,
            "updated_at": now
        }

        unset_fields = {
            "stored_filename": "",
            "content_type": "",
            "file_size": "",
            "photo_uploaded_at": ""
        }

        # Preserve the filename until encrypted-file cleanup succeeds.
        if stored_filename:
            update_fields["photo_cleanup_pending_filename"] = stored_filename
        else:
            unset_fields["photo_cleanup_pending_filename"] = ""

        result = await self.collection.update_one(
            {
                "_id": ObjectId(enrollment_id),
                "organization_id": ObjectId(organization_id),
                "consent_given": True,
                "enrollment_status": {
                    "$in": ["consented", "photo_uploaded"]
                }
            },
            {
                "$set": update_fields,
                "$push": {
                    "consent_history": {
                        "action": "revoked",
                        "consent_version": existing.get("consent_version"),
                        "consented_by": existing.get("consented_by"),
                        "revoked_at": now,
                        "purpose": existing.get("purpose")
                    }
                },
                "$unset": unset_fields
            }
        )
        if result.matched_count == 0:
            return None

        updated_enrollment = await self.get_by_id(
            organization_id,
            enrollment_id
        )

        return {
            "enrollment": updated_enrollment,
            "stored_filename": stored_filename
        }

    
    # RENEW EMPLOYEE FACE ENROLLMENT CONSENT
    async def renew_consent(
        self,
        organization_id: str,
        enrollment_id: str,
        consent_data: dict
    ):

        if not ObjectId.is_valid(organization_id):
            return None

        if not ObjectId.is_valid(enrollment_id):
            return None

        now = datetime.now(timezone.utc)

        new_consent = {
            "consent_given": True,
            "consent_version": consent_data["consent_version"],
            "consented_by": ObjectId(consent_data["consented_by"]),
            "consent_at": now,
            "purpose": consent_data.get(
                "purpose",
                "attendance_verification"
            ),
            "enrollment_status": "consented",
            "updated_at": now
        }

        result = await self.collection.update_one(
            {
                "_id": ObjectId(enrollment_id),
                "organization_id": ObjectId(organization_id),
                "consent_given": False,
                "enrollment_status": "revoked"
            },
            {
                "$set": new_consent,
                "$push": {
                    "consent_history": {
                        "action": "reconsented",
                        "consent_version": consent_data["consent_version"],
                        "consented_by": ObjectId(consent_data["consented_by"]),
                        "consent_at": now,
                        "purpose": consent_data.get(
                            "purpose",
                            "attendance_verification"
                        )
                    }
                },
                "$unset": {
                    "revoked_at": ""
                }
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            enrollment_id
        )



    # UPDATE ENROLLMENT
    async def update(
        self,
        organization_id: str,
        enrollment_id: str,
        update_data: dict
    ):

        if not ObjectId.is_valid(enrollment_id):
            return None

        data = update_data.copy()

        data["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.update_one(
            {
                "_id": ObjectId(enrollment_id),
                "organization_id": ObjectId(organization_id)
            },
            {
                "$set": data
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            enrollment_id
        )

        # CLEAR FACE PHOTO CLEANUP MARKER
    async def clear_photo_cleanup_marker(
        self,
        organization_id: str,
        enrollment_id: str
    ):

        if not ObjectId.is_valid(organization_id):
            return False

        if not ObjectId.is_valid(enrollment_id):
            return False

        result = await self.collection.update_one(
            {
                "_id": ObjectId(enrollment_id),
                "organization_id": ObjectId(organization_id),
                "enrollment_status": "revoked"
            },
            {
                "$unset": {
                    "photo_cleanup_pending_filename": ""
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return result.modified_count > 0
