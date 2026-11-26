
import logging
from datetime import date, datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.attendance_correction_repository import (
    AttendanceCorrectionRepository
)


logger = logging.getLogger(__name__)


class AttendanceCorrectionService:

    def __init__(self, db, mongo_client):
        self.db = db
        self.mongo_client = mongo_client
        self.repository = AttendanceCorrectionRepository(db)
        self.attendance_repository = AttendanceRepository(db)

    # --------------------------------------------------
    # ORGANIZATION VALIDATION
    # --------------------------------------------------

    async def _validate_organization(self, organization_id: str):

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise ValueError("Organization not found or inactive")

        return organization

    # --------------------------------------------------
    # EMPLOYEE VALIDATION
    # --------------------------------------------------

    async def _validate_employee(
        self,
        organization_id: str,
        employee_id: str
    ):

        if not ObjectId.is_valid(employee_id):
            raise ValueError("Invalid employee ID")

        employee = await self.db.employees.find_one({
            "_id": ObjectId(employee_id),
            "organization_id": ObjectId(organization_id),
            "status": "active"
        })

        if not employee:
            raise ValueError("Employee not found or inactive")

        return employee

    # --------------------------------------------------
    # REVIEWER VALIDATION
    # --------------------------------------------------

    def _validate_reviewer(self, current_user: dict):

        allowed_roles = {
            "org_admin",
            "hr_manager"
        }

        user_roles = set(current_user.get("role_names", []))

        if not user_roles.intersection(allowed_roles):
            raise PermissionError(
                "Only organization admins and HR managers "
                "can manage attendance corrections"
            )

        if not ObjectId.is_valid(current_user.get("id")):
            raise ValueError("Invalid authenticated user ID")

    # --------------------------------------------------
    # ORGANIZATION TIMEZONE
    # --------------------------------------------------

    def _get_organization_timezone(self, organization: dict):

        timezone_name = organization.get(
            "timezone",
            "Asia/Kolkata"
        )

        try:
            return ZoneInfo(timezone_name)

        except (ZoneInfoNotFoundError, TypeError):
            raise ValueError(
                "Organization has an invalid timezone configuration"
            )

    # --------------------------------------------------
    # ATTENDANCE DATE VALIDATION
    # --------------------------------------------------

    def _validate_correction_date(
        self,
        correction: dict,
        organization_timezone: ZoneInfo,
    ) -> datetime:

        proposed_event_time = correction["proposed_event_time"]
        attendance_date = correction["attendance_date"]

        # BSON datetimes returned by PyMongo may be timezone-naive.
        # Interpret them as UTC.
        if proposed_event_time.tzinfo is None:
            proposed_event_time = proposed_event_time.replace(
                tzinfo=timezone.utc
            )

        proposed_event_time = proposed_event_time.astimezone(timezone.utc)

        # MongoDB stores attendance_date as UTC midnight.
        if isinstance(attendance_date, datetime):
            attendance_date = attendance_date.date()

        local_event_time = proposed_event_time.astimezone(
            organization_timezone
        )

        if local_event_time.date() != attendance_date:
            raise ValueError(
                "Proposed attendance time must fall on the requested attendance date"
            )

        if proposed_event_time > datetime.now(timezone.utc):
            raise ValueError(
                "Proposed attendance time cannot be in the future"
            )

        return proposed_event_time
    # --------------------------------------------------
    # GET ORGANIZATION DAY BOUNDS
    # --------------------------------------------------

    def _get_day_bounds(self, attendance_date, organization_timezone):

        if isinstance(attendance_date, datetime):
            attendance_date = attendance_date.date()

        if isinstance(attendance_date, str):
            attendance_date = date.fromisoformat(attendance_date)

        local_start = datetime.combine(
            attendance_date,
            time.min,
            tzinfo=organization_timezone
        )

        local_end = datetime.combine(
            attendance_date.replace(day=attendance_date.day),
            time.min,
            tzinfo=organization_timezone
        )

        # Move to the next calendar day.
        from datetime import timedelta
        local_end = local_end + timedelta(days=1)

        return (
            local_start.astimezone(timezone.utc),
            local_end.astimezone(timezone.utc)
        )

    # --------------------------------------------------
    # CREATE CORRECTION REQUEST
    # --------------------------------------------------

    async def create_correction(
        self,
        organization_id: str,
        employee_id: str,
        current_user: dict,
        correction_data
    ):

        organization = await self._validate_organization(
            organization_id
        )

        await self._validate_employee(
            organization_id,
            employee_id
        )

        if current_user.get("employee_id") != employee_id:
            raise PermissionError(
                "You can only request corrections for your own attendance"
            )

        if not ObjectId.is_valid(current_user.get("id")):
            raise ValueError("Invalid authenticated user ID")

        data = correction_data.model_dump()

        correction_type = data["correction_type"]
        original_event_id = data.get("original_event_id")

        organization_timezone = self._get_organization_timezone(
            organization
        )

        proposed_event_time = data["proposed_event_time"]

        if (
            proposed_event_time.tzinfo is None
            or proposed_event_time.utcoffset() is None
        ):
            raise ValueError(
                "Proposed event time must include a timezone"
            )

        proposed_utc = proposed_event_time.astimezone(timezone.utc)

        proposed_local_date = proposed_utc.astimezone(
            organization_timezone
        ).date()

        if proposed_local_date != data["attendance_date"]:
            raise ValueError(
                "Proposed event time does not match attendance date"
            )

        if proposed_utc > datetime.now(timezone.utc):
            raise ValueError(
                "Future attendance corrections are not allowed"
            )

        if original_event_id is not None:

            original_event = await self.attendance_repository.get_by_id(
                organization_id,
                original_event_id
            )

            if not original_event:
                raise ValueError(
                    "Original attendance event not found"
                )

            expected_event_type = (
                "check_in"
                if correction_type == "adjust_check_in"
                else "check_out"
            )

            if original_event.get("event_type") != expected_event_type:
                raise ValueError(
                    "Original attendance event type does not match "
                    "the requested correction"
                )

            original_local_date = original_event["event_time"].astimezone(
                organization_timezone
            ).date()

            if original_local_date != data["attendance_date"]:
                raise ValueError(
                    "Original attendance event does not belong "
                    "to the requested attendance date"
                )

        data["proposed_event_time"] = proposed_utc
        data["organization_id"] = organization_id
        data["employee_id"] = employee_id
        data["created_by_user_id"] = current_user["id"]

        return await self.repository.create(data)

    # --------------------------------------------------
    # GET EMPLOYEE CORRECTIONS
    # --------------------------------------------------

    async def get_employee_corrections(
        self,
        organization_id: str,
        employee_id: str,
        current_user: dict,
        skip: int = 0,
        limit: int = 50
    ):

        await self._validate_organization(organization_id)

        await self._validate_employee(
            organization_id,
            employee_id
        )

        if current_user.get("employee_id") != employee_id:
            raise PermissionError(
                "You can only view your own attendance corrections"
            )

        if skip < 0:
            raise ValueError("Skip cannot be negative")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        return await self.repository.get_by_employee(
            organization_id=organization_id,
            employee_id=employee_id,
            skip=skip,
            limit=limit
        )

    # --------------------------------------------------
    # GET ORGANIZATION CORRECTIONS
    # --------------------------------------------------

    async def get_organization_corrections(
        self,
        organization_id: str,
        current_user: dict,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None
    ):

        await self._validate_organization(organization_id)

        self._validate_reviewer(current_user)

        if skip < 0:
            raise ValueError("Skip cannot be negative")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        return await self.repository.get_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            status=status
        )

    # --------------------------------------------------
    # GET CORRECTION BY ID
    # --------------------------------------------------

    async def get_correction_by_id(
        self,
        organization_id: str,
        correction_id: str,
        current_user: dict
    ):

        await self._validate_organization(organization_id)

        correction = await self.repository.get_by_id(
            organization_id,
            correction_id
        )

        if not correction:
            raise ValueError("Attendance correction not found")

        self._validate_correction_access(
            correction,
            current_user
        )

        return correction

    # --------------------------------------------------
    # CORRECTION ACCESS VALIDATION
    # --------------------------------------------------

    def _validate_correction_access(
        self,
        correction: dict,
        current_user: dict
    ):

        is_owner = (
            str(correction["employee_id"])
            == current_user.get("employee_id")
        )

        if is_owner:
            return

        user_roles = set(current_user.get("role_names", []))

        allowed_roles = {
            "org_admin",
            "hr_manager"
        }

        if not user_roles.intersection(allowed_roles):
            raise PermissionError(
                "You do not have access to this attendance correction"
            )

    # --------------------------------------------------
    # APPROVE CORRECTION
    # --------------------------------------------------

    async def approve_correction(
        self,
        organization_id: str,
        correction_id: str,
        current_user: dict,
        review_reason: str
    ):

        await self._validate_organization(organization_id)

        self._validate_reviewer(current_user)

        correction = await self.repository.get_by_id(
            organization_id,
            correction_id
        )

        if not correction:
            raise ValueError("Attendance correction not found")

        if str(correction["created_by_user_id"]) == current_user["id"]:
            raise PermissionError(
                "You cannot approve your own attendance correction"
            )

        if correction.get("status") != "pending":
            raise ValueError(
                "Only pending correction requests can be approved"
            )

        review_reason = review_reason.strip()

        if len(review_reason) < 5:
            raise ValueError(
                "Review reason must contain at least 5 characters"
            )

        return await self.repository.review(
            organization_id=organization_id,
            correction_id=correction_id,
            reviewer_user_id=current_user["id"],
            status="approved",
            review_reason=review_reason
        )

    # --------------------------------------------------
    # REJECT CORRECTION
    # --------------------------------------------------

    async def reject_correction(
        self,
        organization_id: str,
        correction_id: str,
        current_user: dict,
        review_reason: str
    ):

        await self._validate_organization(organization_id)

        self._validate_reviewer(current_user)

        correction = await self.repository.get_by_id(
            organization_id,
            correction_id
        )

        if not correction:
            raise ValueError("Attendance correction not found")

        if str(correction["created_by_user_id"]) == current_user["id"]:
            raise PermissionError(
                "You cannot reject your own attendance correction"
            )

        if correction.get("status") != "pending":
            raise ValueError(
                "Only pending correction requests can be rejected"
            )

        review_reason = review_reason.strip()

        if len(review_reason) < 5:
            raise ValueError(
                "Review reason must contain at least 5 characters"
            )

        return await self.repository.review(
            organization_id=organization_id,
            correction_id=correction_id,
            reviewer_user_id=current_user["id"],
            status="rejected",
            review_reason=review_reason
        )

    # --------------------------------------------------
    # APPLY MISSING CHECK-IN
    # --------------------------------------------------

    async def _apply_missing_check_in(
        self,
        correction,
        organization_id,
        reviewer_user_id,
        event_time,
        organization_timezone,
        session,
        new_session_id
    ):

        employee_id = str(correction["employee_id"])

        open_session = await self.attendance_repository.get_open_session(
            organization_id,
            employee_id,
            session=session
        )

        if open_session:
            raise ValueError(
                "Cannot apply missing check-in while another "
                "attendance session is open"
            )

        day_start, day_end = self._get_day_bounds(
            correction["attendance_date"],
            organization_timezone
        )

        # Do not insert a historical check-in before already-recorded
        # events later on the same day. That could create an ambiguous
        # session or pair with an unrelated checkout.
        later_event = await self.db.attendance_records.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "employee_id": ObjectId(employee_id),
                "event_time": {
                    "$gte": event_time,
                    "$lt": day_end
                }
            },
            sort=[("event_time", 1)],
            session=session
        )

        if later_event:
            raise ValueError(
                "Cannot apply this missing check-in because later "
                "attendance events already exist for that day"
            )

        return await self.attendance_repository.create(
            {
                "organization_id": organization_id,
                "employee_id": employee_id,
                "session_id": new_session_id,
                "event_type": "check_in",
                "event_time": event_time,
                "source": "admin",
                "created_by_user_id": reviewer_user_id,
                "session_open": True,
                "correction_id": str(correction["_id"])
            },
            session=session
        )

    # --------------------------------------------------
    # APPLY MISSING CHECK-OUT
    # --------------------------------------------------


    async def _apply_missing_check_out(
        self,
        correction,
        organization_id,
        reviewer_user_id,
        event_time,
        organization_timezone,
        session
    ):
        employee_id = str(correction["employee_id"])

        open_session = await self.attendance_repository.get_open_session(
            organization_id,
            employee_id,
            session=session
        )

        if not open_session:
            raise ValueError(
                "Cannot apply missing check-out because "
                "no open attendance session exists"
            )

        # Normalize MongoDB BSON datetime to UTC.
        check_in_time = open_session["event_time"]

        if check_in_time.tzinfo is None:
            check_in_time = check_in_time.replace(
                tzinfo=timezone.utc
            )

        check_in_time = check_in_time.astimezone(timezone.utc)

        # Normalize proposed checkout time as well.
        if event_time.tzinfo is None:
            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        event_time = event_time.astimezone(timezone.utc)

        check_in_local_date = check_in_time.astimezone(
            organization_timezone
        ).date()

        attendance_date = correction["attendance_date"]

        if isinstance(attendance_date, datetime):
            attendance_date = attendance_date.date()

        if check_in_local_date != attendance_date:
            raise ValueError(
                "The open attendance session does not belong "
                "to the correction attendance date"
            )

        if event_time <= check_in_time:
            raise ValueError(
                "Proposed check-out time must be later than check-in time"
            )

        _, day_end = self._get_day_bounds(
            attendance_date,
            organization_timezone
        )

        later_event = await self.db.attendance_records.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "employee_id": ObjectId(employee_id),
                "event_time": {
                    "$gt": event_time,
                    "$lt": day_end
                }
            },
            session=session
        )

        if later_event:
            raise ValueError(
                "Cannot apply missing check-out because later "
                "attendance events already exist for that day"
            )

        checkout_event = await self.attendance_repository.create(
            {
                "organization_id": organization_id,
                "employee_id": employee_id,
                "session_id": open_session["session_id"],
                "event_type": "check_out",
                "event_time": event_time,
                "source": "admin",
                "created_by_user_id": reviewer_user_id,
                "correction_id": str(correction["_id"])
            },
            session=session
        )

        if checkout_event is None:
            raise RuntimeError(
                "Corrected check-out event could not be created"
            )

        closed = await self.attendance_repository.close_session(
            org_id=organization_id,
            attendance_id=str(open_session["_id"]),
            checkout_event_id=str(checkout_event["_id"]),
            session=session
        )

        if not closed:
            raise ValueError(
                "Unable to close the attendance session"
            )

        return checkout_event


    # --------------------------------------------------
    # VALIDATE ORIGINAL EVENT FOR ADJUSTMENT
    # --------------------------------------------------

    async def _validate_adjustment_original(
        self,
        correction,
        organization_id,
        event_time,
        organization_timezone,
        session
    ):

        original_event_id = correction.get("original_event_id")

        if not original_event_id:
            raise ValueError(
                "Original attendance event is required for adjustments"
            )

        original_event = await self.attendance_repository.get_by_id(
            organization_id,
            str(original_event_id),
            session=session
        )

        if not original_event:
            raise ValueError("Original attendance event not found")

        expected_type = (
            "check_in"
            if correction["correction_type"] == "adjust_check_in"
            else "check_out"
        )

        if original_event.get("event_type") != expected_type:
            raise ValueError(
                "Original attendance event type does not match correction"
            )

        employee_id = str(correction["employee_id"])

        if str(original_event["employee_id"]) != employee_id:
            raise ValueError(
                "Original attendance event belongs to another employee"
            )

        original_local_date = original_event["event_time"].astimezone(
            organization_timezone
        ).date()

        attendance_date = correction["attendance_date"]

        if isinstance(attendance_date, datetime):
            attendance_date = attendance_date.date()

        if original_local_date != attendance_date:
            raise ValueError(
                "Original attendance event does not belong "
                "to the correction attendance date"
            )

        # Do not allow a second applied correction to supersede
        # the same original event.
        existing_applied_correction = (
            await self.db.attendance_corrections.find_one(
                {
                    "_id": {"$ne": correction["_id"]},
                    "organization_id": ObjectId(organization_id),
                    "original_event_id": ObjectId(original_event_id),
                    "status": "applied"
                },
                session=session
            )
        )

        if existing_applied_correction:
            raise ValueError(
                "This original attendance event has already "
                "been corrected"
            )

        return original_event

    # --------------------------------------------------
    # APPLY ADJUSTED CHECK-IN
    # --------------------------------------------------

    async def _apply_adjust_check_in(
        self,
        correction,
        organization_id,
        reviewer_user_id,
        event_time,
        organization_timezone,
        session
    ):

        original_event = await self._validate_adjustment_original(
            correction,
            organization_id,
            event_time,
            organization_timezone,
            session
        )

        session_id = original_event.get("session_id")

        if not session_id:
            raise ValueError(
                "Original check-in does not have a valid session ID"
            )

        checkout_event = await self.db.attendance_records.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "employee_id": correction["employee_id"],
                "session_id": session_id,
                "event_type": "check_out"
            },
            session=session
        )

        if checkout_event:
            checkout_time = checkout_event["event_time"]

            # MongoDB BSON datetime values may be timezone-naive.
            # Interpret naive values as UTC.
            if checkout_time.tzinfo is None:
                checkout_time = checkout_time.replace(
                    tzinfo=timezone.utc
                )

            checkout_time = checkout_time.astimezone(timezone.utc)

            if event_time >= checkout_time:
                raise ValueError(
                    "Corrected check-in time must be earlier than "
                    "the existing check-out time"
                )

        if event_time == original_event["event_time"]:
            raise ValueError(
                "Adjusted check-in time must differ from original time"
            )

        # The original check-in remains responsible for the open-session
        # index and session closure. The replacement is an audit event,
        # not a second open session.
        return await self.attendance_repository.create(
            {
                "organization_id": organization_id,
                "employee_id": str(correction["employee_id"]),
                "session_id": session_id,
                "event_type": "check_in",
                "event_time": event_time,
                "source": "admin",
                "created_by_user_id": reviewer_user_id,
                "correction_id": str(correction["_id"]),
                "corrects_event_id": str(original_event["_id"])
            },
            session=session
        )

    # --------------------------------------------------
    # APPLY ADJUSTED CHECK-OUT
    # --------------------------------------------------


    
    async def _apply_adjust_check_out(
        self,
        correction,
        organization_id,
        reviewer_user_id,
        event_time,
        organization_timezone,
        session
    ):
        original_event = await self._validate_adjustment_original(
            correction,
            organization_id,
            event_time,
            organization_timezone,
            session
        )

        session_id = original_event.get("session_id")

        if not session_id:
            raise ValueError(
                "Original check-out does not have a valid session ID"
            )

        check_in_event = await self.db.attendance_records.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "employee_id": correction["employee_id"],
                "session_id": session_id,
                "event_type": "check_in"
            },
            session=session
        )

        if not check_in_event:
            raise ValueError(
                "Matching check-in event for the original check-out "
                "could not be found"
            )

        check_in_time = check_in_event["event_time"]

        if check_in_time.tzinfo is None:
            check_in_time = check_in_time.replace(tzinfo=timezone.utc)

        check_in_time = check_in_time.astimezone(timezone.utc)

        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        event_time = event_time.astimezone(timezone.utc)

        if event_time <= check_in_time:
            raise ValueError(
                "Adjusted check-out must be later than its check-in"
            )

        original_event_time = original_event["event_time"]

        if original_event_time.tzinfo is None:
            original_event_time = original_event_time.replace(
                tzinfo=timezone.utc
            )

        original_event_time = original_event_time.astimezone(timezone.utc)

        if event_time == original_event_time:
            raise ValueError(
                "Adjusted check-out time must differ from original time"
            )

        replacement_event = await self.attendance_repository.create(
            {
                "organization_id": organization_id,
                "employee_id": str(correction["employee_id"]),
                "session_id": session_id,
                "event_type": "check_out",
                "event_time": event_time,
                "source": "admin",
                "created_by_user_id": reviewer_user_id,
                "correction_id": str(correction["_id"]),
                "corrects_event_id": str(original_event["_id"])
            },
            session=session
        )

        if not replacement_event:
            raise ValueError(
                "Failed to create replacement checkout event"
            )

        reference_updated = (
            await self.attendance_repository.update_session_checkout_reference(
                organization_id,
                str(check_in_event["_id"]),
                str(original_event["_id"]),
                replacement_event["id"],
                session=session
            )
        )

        if not reference_updated:
            raise ValueError(
                "Failed to update the attendance session checkout reference"
            )

        return replacement_event



    # --------------------------------------------------
    # APPLY APPROVED CORRECTION
    # --------------------------------------------------

    async def apply_correction(
        self,
        organization_id: str,
        correction_id: str,
        current_user: dict
    ):

        organization = await self._validate_organization(
            organization_id
        )

        self._validate_reviewer(current_user)

        if not ObjectId.is_valid(correction_id):
            raise ValueError("Invalid correction ID")

        reviewer_user_id = current_user["id"]

        organization_timezone = self._get_organization_timezone(
            organization
        )

        new_session_id = str(uuid4())
        applied_event_time = datetime.now(timezone.utc)

        async def transaction_callback(session):

            correction = await self.repository.get_by_id(
                organization_id,
                correction_id,
                session=session
            )

            if not correction:
                raise ValueError("Attendance correction not found")

            # Idempotent retry after a successful application.
            if correction.get("status") == "applied":
                return correction

            if correction.get("status") != "approved":
                raise ValueError(
                    "Only approved correction requests can be applied"
                )

            if (
                str(correction["created_by_user_id"])
                == reviewer_user_id
            ):
                raise PermissionError(
                    "The correction requester cannot apply their own correction"
                )

            await self._validate_employee(
                organization_id,
                str(correction["employee_id"])
            )

            event_time = self._validate_correction_date(
                correction,
                organization_timezone
            )

            # Extra idempotency check inside the transaction.
            existing_event = (
                await self.attendance_repository.get_by_correction_id(
                    organization_id,
                    correction_id,
                    session=session
                )
            )

            if existing_event:
                raise ValueError(
                    "An attendance event already exists for this correction"
                )

            correction_type = correction["correction_type"]

            if correction_type == "missing_check_in":

                attendance_event = await self._apply_missing_check_in(
                    correction,
                    organization_id,
                    reviewer_user_id,
                    event_time,
                    organization_timezone,
                    session,
                    new_session_id
                )

            elif correction_type == "missing_check_out":

                attendance_event = await self._apply_missing_check_out(
                    correction,
                    organization_id,
                    reviewer_user_id,
                    event_time,
                    organization_timezone,
                    session
                )

            elif correction_type == "adjust_check_in":

                attendance_event = await self._apply_adjust_check_in(
                    correction,
                    organization_id,
                    reviewer_user_id,
                    event_time,
                    organization_timezone,
                    session
                )

            elif correction_type == "adjust_check_out":

                attendance_event = await self._apply_adjust_check_out(
                    correction,
                    organization_id,
                    reviewer_user_id,
                    event_time,
                    organization_timezone,
                    session
                )

            else:
                raise ValueError("Unsupported attendance correction type")

            if attendance_event is None:
                raise RuntimeError(
                    "Corrected attendance event could not be created"
                )

            updated_correction = await self.repository.mark_applied(
                organization_id=organization_id,
                correction_id=correction_id,
                applied_event_id=str(attendance_event["_id"]),
                session=session
            )

            if updated_correction is None:
                raise ValueError(
                    "Correction could not be marked as applied"
                )

            return updated_correction

        try:
            async with self.mongo_client.start_session() as session:
                return await session.with_transaction(
                    transaction_callback
                )

        except DuplicateKeyError:

            # Recover from a concurrent retry only when the database
            # confirms that the correction was successfully applied.
            correction = await self.repository.get_by_id(
                organization_id,
                correction_id
            )

            existing_event = (
                await self.attendance_repository.get_by_correction_id(
                    organization_id,
                    correction_id
                )
            )

            if (
                correction
                and correction.get("status") == "applied"
                and existing_event
                and str(correction.get("applied_event_id"))
                == str(existing_event["_id"])
            ):
                return correction

            raise ValueError(
                "Correction application conflicted with another request"
            )

        except Exception:
            logger.exception(
                "Unexpected error applying attendance correction"
            )
            raise
