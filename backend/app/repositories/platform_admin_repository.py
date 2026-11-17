from datetime import datetime, timezone
from bson import ObjectId


class PlatformAdminRepository:

    def __init__(self, db):
        self.collection = db.platform_admins

    # -----------------------------------------
    # CREATE PLATFORM ADMIN
    # -----------------------------------------

    async def create(self, admin_data: dict):

        admin_data = admin_data.copy()

        email = admin_data.get("email")

        if not email:
            raise ValueError("Email is required")

        admin_data["email"] = email.strip().lower()

        now = datetime.now(timezone.utc)

        admin_data.setdefault("created_at", now)
        admin_data.setdefault("updated_at", now)
        admin_data.setdefault("status", "active")

        result = await self.collection.insert_one(
            admin_data
        )

        return await self.get_by_id(
            str(result.inserted_id)
        )

    # -----------------------------------------
    # FIND ADMIN BY EMAIL
    # -----------------------------------------

    async def get_by_email(self, email: str):

        return await self.collection.find_one(
            {
                "email": email.strip().lower()
            }
        )

    # -----------------------------------------
    # FIND ADMIN BY ID
    # -----------------------------------------

    async def get_by_id(self, admin_id: str):

        if not ObjectId.is_valid(admin_id):
            return None

        return await self.collection.find_one(
            {
                "_id": ObjectId(admin_id)
            }
        )

    # -----------------------------------------
    # UPDATE LAST LOGIN
    # -----------------------------------------

    async def update_last_login(self, admin_id: str):

        if not ObjectId.is_valid(admin_id):
            return None

        now = datetime.now(timezone.utc)

        await self.collection.update_one(
            {
                "_id": ObjectId(admin_id)
            },
            {
                "$set": {
                    "last_login": now,
                    "updated_at": now
                }
            }
        )

        return await self.get_by_id(admin_id)

    # -----------------------------------------
    # UPDATE ACCOUNT STATUS
    # -----------------------------------------

    async def update_status(
        self,
        admin_id: str,
        status: str
    ):

        allowed_statuses = {"active", "inactive"}

        if status not in allowed_statuses:
            raise ValueError("Invalid account status")

        if not ObjectId.is_valid(admin_id):
            return None

        await self.collection.update_one(
            {
                "_id": ObjectId(admin_id)
            },
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return await self.get_by_id(admin_id)


    # -----------------------------------------
    # COUNT PLATFORM ADMINS
    # -----------------------------------------

    async def count_admins(self):

        return await self.collection.count_documents({})
