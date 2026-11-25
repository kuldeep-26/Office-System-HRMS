
from datetime import datetime, timezone

from bson import ObjectId


class AttendanceRepository:

    def __init__(self, db):
        self.collection = db.attendance_records


    # CREATE ATTENDANCE EVENT
    async def create(self, attendance_data: dict, session=None):
        data = attendance_data.copy()
        data["organization_id"] = ObjectId(data["organization_id"])
        data["employee_id"] = ObjectId(data["employee_id"])

        created_by_user_id = data.get("created_by_user_id")

        if not ObjectId.is_valid(created_by_user_id):
            raise ValueError("Invalid attendance actor user ID")

        data["created_by_user_id"] = ObjectId(created_by_user_id)

        data["created_at"] = datetime.now(timezone.utc)

        insert_options = {}
        if session is not None:
            insert_options["session"] = session

        result = await self.collection.insert_one(
            data,
            **insert_options
        )

        return await self.get_by_id(
            organization_id=str(data["organization_id"]),
            attendance_id=str(result.inserted_id),
            session=session
        )


    # GET ATTENDANCE EVENT BY ID
    async def get_by_id(
        self,
        organization_id: str,
        attendance_id: str,
        session=None
    ):

        if (
            not ObjectId.is_valid(organization_id)
            or not ObjectId.is_valid(attendance_id)
        ):
            return None

        find_options = {}
        if session is not None:
            find_options["session"] = session

        document = await self.collection.find_one(
            {
                "_id": ObjectId(attendance_id),
                "organization_id": ObjectId(organization_id)
            },
            **find_options
        )
        return document

    # GET EMPLOYEE ATTENDANCE HISTORY
    async def get_by_employee(
        self,
        organization_id: str,
        employee_id: str,
        skip: int = 0,
        limit: int = 50,
        session=None
    ):
        if (
            not ObjectId.is_valid(organization_id)
            or not ObjectId.is_valid(employee_id)
        ):
            return []

        find_options = {}
        if session is not None:
            find_options["session"] = session

        cursor = (
            self.collection
            .find(
                {
                    "organization_id": ObjectId(organization_id),
                    "employee_id": ObjectId(employee_id)
                },
                **find_options
            )
            .sort([
                ("event_time", -1),
                ("_id", -1)
            ])
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)


    # GET LATEST EMPLOYEE ATTENDANCE EVENT
    async def get_latest_by_employee(
        self,
        organization_id: str,
        employee_id: str,
        session=None
    ):
        if (
            not ObjectId.is_valid(organization_id)
            or not ObjectId.is_valid(employee_id)
        ):
            return None

        find_options = {}
        if session is not None:
            find_options["session"] = session

        return await self.collection.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "employee_id": ObjectId(employee_id)
            },
            sort=[
                ("event_time", -1),
                ("_id", -1)
            ],
            **find_options
        )


    # GET EMPLOYEE'S OPEN ATTENDANCE SESSION
    async def get_open_session(self, org_id: str, employee_id: str, session=None):
        if not ObjectId.is_valid(org_id) or not ObjectId.is_valid(employee_id):
            return None

        find_options = {}
        if session is not None:
            find_options["session"] = session

        return await self.collection.find_one(
            {
                "organization_id": ObjectId(org_id),
                "employee_id": ObjectId(employee_id),
                "event_type": "check_in",
                "session_open": True
            },
            sort=[("event_time", -1), ("_id", -1)],
            **find_options
        )

    # CLOSE EMPLOYEE ATTENDANCE SESSION
    async def close_session(
        self,
        org_id: str,
        attendance_id: str,
        checkout_event_id: str,
        session=None
    ):
        if not all(
            ObjectId.is_valid(value)
            for value in (org_id, attendance_id, checkout_event_id)
        ):
            return False

        update_options = {}
        if session is not None:
            update_options["session"] = session

        result = await self.collection.update_one(
            {
                "_id": ObjectId(attendance_id),
                "organization_id": ObjectId(org_id),
                "event_type": "check_in",
                "session_open": True
            },
            {
                "$set": {
                    "session_open": False,
                    "checkout_event_id": ObjectId(checkout_event_id),
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            **update_options
        )

        return result.modified_count == 1



    # GET ORGANIZATION ATTENDANCE RECORDS
    async def get_by_organization(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 50,
        session=None
    ):
        if not ObjectId.is_valid(organization_id):
            return []

        find_options = {}
        if session is not None:
            find_options["session"] = session

        cursor = (
            self.collection
            .find(
                {
                    "organization_id": ObjectId(organization_id)
                },
                **find_options
            )
            .sort([
                ("event_time", -1),
                ("_id", -1)
            ])
            .skip(skip)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)


    # GET EVENT BY IDEMPOTENCY KEY
    async def get_by_idempotency_key(
        self,
        org_id: str,
        idempotency_key: str,
        session=None
    ):
        if not ObjectId.is_valid(org_id):
            return None

        find_options = {}
        if session is not None:
            find_options["session"] = session

        return await self.collection.find_one(
            {
                "organization_id": ObjectId(org_id),
                "idempotency_key": idempotency_key
            },
            **find_options
        )
