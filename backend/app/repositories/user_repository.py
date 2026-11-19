from datetime import datetime, timezone
from bson import ObjectId


class UserRepository:

    def __init__(self, db):
        self.collection = db.users

    
    # -----------------------------------------
    # CREATE USER
    # -----------------------------------------

    async def create(self, user_data: dict):

        user_data = user_data.copy()

        # 1. Validate organization ID
        organization_id = user_data.get("organization_id")

        if isinstance(organization_id, str):
            if not ObjectId.is_valid(organization_id):
                raise ValueError("Invalid organization ID")

            organization_id = ObjectId(organization_id)

        elif not isinstance(organization_id, ObjectId):
            raise ValueError("Valid organization ID required")

        user_data["organization_id"] = organization_id

        # 2. Normalize role IDs
        role_ids = user_data.get("role_ids", [])

        if not isinstance(role_ids, list):
            raise ValueError("role_ids must be a list")

        normalized_role_ids = []

        for role_id in role_ids:

            if isinstance(role_id, str):
                if not ObjectId.is_valid(role_id):
                    raise ValueError("Invalid role ID")

                role_id = ObjectId(role_id)

            elif not isinstance(role_id, ObjectId):
                raise ValueError("Valid role ID required")

            normalized_role_ids.append(role_id)

        user_data["role_ids"] = normalized_role_ids

        # 3. Normalize employee ID
        employee_id = user_data.get("employee_id")

        if isinstance(employee_id, str):
            if not ObjectId.is_valid(employee_id):
                raise ValueError("Invalid employee ID")

            user_data["employee_id"] = ObjectId(employee_id)

        elif employee_id is not None and not isinstance(
            employee_id, ObjectId
        ):
            raise ValueError("Valid employee ID required")

        # 4. Add timestamps and default status
        now = datetime.now(timezone.utc)

        user_data.setdefault("created_at", now)
        user_data.setdefault("updated_at", now)
        user_data.setdefault("status", "active")

        # 5. Insert user
        result = await self.collection.insert_one(user_data)

        # 6. Return inserted document
        return await self.collection.find_one({
            "_id": result.inserted_id,
            "organization_id": organization_id
        })


    # -----------------------------------------
    # FIND USER BY EMAIL
    # -----------------------------------------

    async def get_by_email(
        self,
        organization_id: str,
        email: str
    ):

        if not ObjectId.is_valid(organization_id):
            return None

        return await self.collection.find_one(
            {
                "organization_id": ObjectId(organization_id),
                "email": email.strip().lower()
            }
        )

    # -----------------------------------------
    # FIND USER BY ID
    # -----------------------------------------

    async def get_by_id(
        self,
        user_id: str,
        organization_id: str
    ):

        if not ObjectId.is_valid(user_id):
            return None

        if not ObjectId.is_valid(organization_id):
            return None

        return await self.collection.find_one(
            {
                "_id": ObjectId(user_id),
                "organization_id": ObjectId(organization_id)
            }
        )

    # -----------------------------------------
    # UPDATE LAST LOGIN
    # -----------------------------------------

    async def update_last_login(
        self,
        user_id: str,
        organization_id: str
    ):

        if not ObjectId.is_valid(user_id):
            return None

        if not ObjectId.is_valid(organization_id):
            return None

        await self.collection.update_one(
            {
                "_id": ObjectId(user_id),
                "organization_id": ObjectId(organization_id)
            },
            {
                "$set": {
                    "last_login": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return await self.get_by_id(
            user_id,
            organization_id
        )

    # -----------------------------------------
    # UPDATE ACCOUNT STATUS
    # -----------------------------------------

    async def update_status(
        self,
        user_id: str,
        organization_id: str,
        status: str
    ):

        if not ObjectId.is_valid(user_id):
            return None

        if not ObjectId.is_valid(organization_id):
            return None

        await self.collection.update_one(
            {
                "_id": ObjectId(user_id),
                "organization_id": ObjectId(organization_id)
            },
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return await self.get_by_id(
            user_id,
            organization_id
        )
