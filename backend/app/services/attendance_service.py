
from datetime import datetime, timezone
from uuid import uuid4
import logging

from pymongo.errors import DuplicateKeyError

from app.repositories.attendance_repository import AttendanceRepository


logger = logging.getLogger(__name__)


class AttendanceService:

    def __init__(self, db, mongo_client):
        self.repository = AttendanceRepository(db)
        self.mongo_client = mongo_client

    
    async def _validate_organization(self, organization_id: str):
        from bson import ObjectId

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        organization = await self.repository.collection.database.organizations.find_one(
            {
                "_id": ObjectId(organization_id),
                "status": "active"
            }
        )

        if not organization:
            raise ValueError("Organization not found or inactive")

        return organization

    async def _validate_employee(self, organization_id: str, employee_id: str):
        from bson import ObjectId

        if not ObjectId.is_valid(employee_id):
            raise ValueError("Invalid employee ID")

        employee = await self.repository.collection.database.employees.find_one(
            {
                "_id": ObjectId(employee_id),
                "organization_id": ObjectId(organization_id),
                "status": "active"
            }
        )

        if not employee:
            raise ValueError("Employee not found or inactive")

        return employee

    
    async def _validate_employee_access(
        self,
        current_user: dict,
        employee_id: str
    ):
        if current_user.get("employee_id") != employee_id:
            raise PermissionError(
                "You can only manage your own attendance"
            )

    



    async def check_in(
        self,
        organization_id: str,
        employee_id: str,
        current_user: dict,
        idempotency_key: str
    ):
        await self._validate_organization(organization_id)
        await self._validate_employee(organization_id, employee_id)
        await self._validate_employee_access(current_user, employee_id)

        if not idempotency_key or not 10 <= len(idempotency_key) <= 100:
            raise ValueError("Invalid idempotency key")

        session_id = str(uuid4())
        event_time = datetime.now(timezone.utc)

        async def transaction_callback(session):
            existing = await self.repository.get_by_idempotency_key(
                organization_id,
                idempotency_key,
                session=session
            )

            if existing:
                if (
                    str(existing.get("employee_id")) == employee_id
                    and existing.get("event_type") == "check_in"
                ):
                    return existing

                raise ValueError(
                    "Idempotency key has already been used"
                )

            open_session = await self.repository.get_open_session(
                organization_id,
                employee_id,
                session=session
            )

            if open_session:
                raise ValueError(
                    "You already have an open attendance session"
                )

            attendance_data = {
                "organization_id": organization_id,
                "employee_id": employee_id,
                "session_id": session_id,
                "event_type": "check_in",
                "event_time": event_time,
                "source": "web",
                "created_by_user_id": current_user["id"],
                "idempotency_key": idempotency_key,
                "session_open": True
            }

            return await self.repository.create(
                attendance_data,
                session=session
            )

        try:
            async with self.mongo_client.start_session() as session:
                return await session.with_transaction(
                    transaction_callback
                )

        except DuplicateKeyError:
            existing = await self.repository.get_by_idempotency_key(
                organization_id,
                idempotency_key
            )

            if existing:
                if (
                    str(existing.get("employee_id")) == employee_id
                    and existing.get("event_type") == "check_in"
                ):
                    return existing

                raise ValueError(
                    "Idempotency key has already been used"
                )

            raise ValueError(
                "An attendance session is already open or "
                "the check-in request conflicted with another request"
            )

        except Exception:
            logger.exception(
                "Unexpected error during attendance check-in transaction"
            )
            raise


    async def check_out(
        self,
        organization_id: str,
        employee_id: str,
        current_user: dict,
        idempotency_key: str
    ):
        await self._validate_organization(organization_id)
        await self._validate_employee(organization_id, employee_id)
        await self._validate_employee_access(current_user, employee_id)

        if not idempotency_key or not 10 <= len(idempotency_key) <= 100:
            raise ValueError("Invalid idempotency key")

        async def transaction_callback(session):
            existing = await self.repository.get_by_idempotency_key(
                organization_id,
                idempotency_key,
                session=session
            )

            if existing:
                if (
                    str(existing.get("employee_id")) == employee_id
                    and existing.get("event_type") == "check_out"
                ):
                    return existing

                raise ValueError(
                    "Idempotency key has already been used"
                )

            open_session = await self.repository.get_open_session(
                organization_id,
                employee_id,
                session=session
            )

            if not open_session:
                raise ValueError(
                    "No open attendance session found"
                )

            checkout_event = await self.repository.create(
                {
                    "organization_id": organization_id,
                    "employee_id": employee_id,
                    "session_id": open_session["session_id"],
                    "event_type": "check_out",
                    "event_time": datetime.now(timezone.utc),
                    "source": "web",
                    "created_by_user_id": current_user["id"],
                    "idempotency_key": idempotency_key
                },
                session=session
            )

            if checkout_event is None:
                raise RuntimeError(
                    "Checkout event could not be created"
                )

            closed = await self.repository.close_session(
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

        try:
            async with self.mongo_client.start_session() as session:
                return await session.with_transaction(
                    transaction_callback
                )

        except DuplicateKeyError:
            existing = await self.repository.get_by_idempotency_key(
                organization_id,
                idempotency_key
            )

            if existing:
                if (
                    str(existing.get("employee_id")) == employee_id
                    and existing.get("event_type") == "check_out"
                ):
                    return existing

                raise ValueError(
                    "Idempotency key has already been used"
                )

            raise ValueError(
                "Attendance check-out conflicted with another request"
            )

        except Exception:
            logger.exception(
                "Unexpected error during attendance check-out transaction"
            )
            raise



    async def get_employee_attendance(
        self,
        organization_id: str,
        employee_id: str,
        current_user: dict,
        skip: int = 0,
        limit: int = 50
    ):
        await self._validate_organization(organization_id)
        await self._validate_employee(organization_id, employee_id)
        await self._validate_employee_access(current_user, employee_id)

        if skip < 0:
            raise ValueError("Skip cannot be negative")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        records = await self.repository.get_effective_by_employee(
            organization_id=organization_id,
            employee_id=employee_id,
            skip=skip,
            limit=limit
        )

        return records



    async def get_organization_attendance(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 50
    ):
        await self._validate_organization(organization_id)

        if skip < 0:
            raise ValueError("Skip cannot be negative")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        records = await self.repository.get_effective_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit
        )

        return records
