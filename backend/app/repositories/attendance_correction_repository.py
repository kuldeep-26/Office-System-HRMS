
from datetime import datetime, timezone, time

from bson import ObjectId


class AttendanceCorrectionRepository:

    def __init__(self, db):
        self.collection = db.attendance_corrections

    # --------------------------------------------------
    # CREATE CORRECTION REQUEST
    # --------------------------------------------------

    async def create(self, correction_data, session=None):
        """
        Create a new attendance correction request.
        """

        data = correction_data.copy()

        organization_id = data.get("organization_id")
        employee_id = data.get("employee_id")
        created_by_user_id = data.get("created_by_user_id")

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(employee_id):
            raise ValueError("Invalid employee ID")

        if not ObjectId.is_valid(created_by_user_id):
            raise ValueError("Invalid creator user ID")

        data["organization_id"] = ObjectId(organization_id)
        data["employee_id"] = ObjectId(employee_id)
        data["created_by_user_id"] = ObjectId(created_by_user_id)

        original_event_id = data.get("original_event_id")

        if original_event_id is not None:
            if not ObjectId.is_valid(original_event_id):
                raise ValueError("Invalid original attendance event ID")

            data["original_event_id"] = ObjectId(original_event_id)

        attendance_date = data.get("attendance_date")

        if isinstance(attendance_date, str):
            attendance_date = datetime.strptime(
                attendance_date,
                "%Y-%m-%d"
            ).date()

        if not hasattr(attendance_date, "year"):
            raise ValueError("Invalid attendance date")

        data["attendance_date"] = datetime.combine(
            attendance_date,
            time.min,
            tzinfo=timezone.utc
        )

        proposed_event_time = data.get("proposed_event_time")

        if (
            not isinstance(proposed_event_time, datetime)
            or proposed_event_time.tzinfo is None
            or proposed_event_time.utcoffset() is None
        ):
            raise ValueError(
                "Proposed event time must include a timezone"
            )

        data["proposed_event_time"] = proposed_event_time.astimezone(
            timezone.utc
        )

        data["status"] = "pending"

        now = datetime.now(timezone.utc)
        data["created_at"] = now
        data["updated_at"] = now

        insert_options = {}

        if session is not None:
            insert_options["session"] = session

        result = await self.collection.insert_one(
            data,
            **insert_options
        )

        return await self.get_by_id(
            str(data["organization_id"]),
            str(result.inserted_id),
            session=session
        )

    # --------------------------------------------------
    # GET CORRECTION BY ID
    # --------------------------------------------------

    async def get_by_id(
        self,
        organization_id,
        correction_id,
        session=None
    ):
        """
        Retrieve a correction request within an organization.
        """

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(correction_id):
            raise ValueError("Invalid correction ID")

        find_options = {}

        if session is not None:
            find_options["session"] = session

        return await self.collection.find_one(
            {
                "_id": ObjectId(correction_id),
                "organization_id": ObjectId(organization_id)
            },
            **find_options
        )

    # --------------------------------------------------
    # GET EMPLOYEE CORRECTIONS
    # --------------------------------------------------

    async def get_by_employee(
        self,
        organization_id,
        employee_id,
        skip=0,
        limit=50,
        session=None
    ):
        """
        Retrieve correction requests belonging to one employee.
        """

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(employee_id):
            raise ValueError("Invalid employee ID")

        find_options = {}

        if session is not None:
            find_options["session"] = session

        cursor = (
            self.collection.find(
                {
                    "organization_id": ObjectId(organization_id),
                    "employee_id": ObjectId(employee_id)
                },
                **find_options
            )
            .sort([
                ("created_at", -1),
                ("_id", -1)
            ])
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    # --------------------------------------------------
    # GET ORGANIZATION CORRECTIONS
    # --------------------------------------------------

    async def get_by_organization(
        self,
        organization_id,
        skip=0,
        limit=50,
        status=None,
        session=None
    ):
        """
        Retrieve correction requests belonging to an organization.
        Optionally filter by correction status.
        """

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        query = {
            "organization_id": ObjectId(organization_id)
        }

        if status is not None:
            allowed_statuses = {
                "pending",
                "approved",
                "rejected",
                "applied"
            }

            if status not in allowed_statuses:
                raise ValueError("Invalid correction status")

            query["status"] = status

        find_options = {}

        if session is not None:
            find_options["session"] = session

        cursor = (
            self.collection.find(query, **find_options)
            .sort([
                ("created_at", -1),
                ("_id", -1)
            ])
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    # --------------------------------------------------
    # APPROVE OR REJECT CORRECTION
    # --------------------------------------------------

    async def review(
        self,
        organization_id,
        correction_id,
        reviewer_user_id,
        status,
        review_reason,
        session=None
    ):
        """
        Approve or reject a pending correction request.
        Only one review can succeed.
        """

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(correction_id):
            raise ValueError("Invalid correction ID")

        if not ObjectId.is_valid(reviewer_user_id):
            raise ValueError("Invalid reviewer user ID")

        if status not in {"approved", "rejected"}:
            raise ValueError("Invalid review status")

        now = datetime.now(timezone.utc)

        update_options = {}

        if session is not None:
            update_options["session"] = session

        result = await self.collection.update_one(
            {
                "_id": ObjectId(correction_id),
                "organization_id": ObjectId(organization_id),
                "status": "pending"
            },
            {
                "$set": {
                    "status": status,
                    "reviewed_by_user_id": ObjectId(reviewer_user_id),
                    "reviewed_at": now,
                    "review_reason": review_reason,
                    "updated_at": now
                }
            },
            **update_options
        )

        if result.modified_count != 1:
            return None

        return await self.get_by_id(
            organization_id,
            correction_id,
            session=session
        )

    # --------------------------------------------------
    # MARK CORRECTION AS APPLIED
    # --------------------------------------------------

    async def mark_applied(
        self,
        organization_id,
        correction_id,
        applied_event_id,
        session=None
    ):
        """
        Mark an approved correction as applied.

        This method can participate in a MongoDB transaction
        so the attendance event and correction status update
        can be committed atomically.
        """

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(correction_id):
            raise ValueError("Invalid correction ID")

        if not ObjectId.is_valid(applied_event_id):
            raise ValueError("Invalid applied attendance event ID")

        now = datetime.now(timezone.utc)

        update_options = {}

        if session is not None:
            update_options["session"] = session

        result = await self.collection.update_one(
            {
                "_id": ObjectId(correction_id),
                "organization_id": ObjectId(organization_id),
                "status": "approved",
                "applied_event_id": {"$exists": False}
            },
            {
                "$set": {
                    "status": "applied",
                    "applied_event_id": ObjectId(applied_event_id),
                    "applied_at": now,
                    "updated_at": now
                }
            },
            **update_options
        )

        if result.modified_count != 1:
            return None

        return await self.get_by_id(
            organization_id,
            correction_id,
            session=session
        )
