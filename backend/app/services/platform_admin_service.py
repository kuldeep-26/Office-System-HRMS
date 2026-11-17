
from datetime import datetime, timezone

from app.core.security import hash_password
from app.repositories.platform_admin_repository import (
    PlatformAdminRepository
)


class PlatformAdminService:

    def __init__(self, db):
        self.repository = PlatformAdminRepository(db)

    # -----------------------------------------
    # CREATE FIRST SUPER ADMIN
    # -----------------------------------------

    async def create_first_admin(
        self,
        full_name: str,
        email: str,
        password: str
    ) -> dict:

        # 1. Validate input
        full_name = full_name.strip()
        email = email.strip().lower()

        if not full_name:
            raise ValueError("Full name is required")

        if not email:
            raise ValueError("Email is required")

        if len(password) < 10:
            raise ValueError(
                "Password must contain at least 12 characters"
            )

        # 2. Ensure this is the first platform admin
        existing_count = await self.repository.count_admins()

        if existing_count > 0:
            raise ValueError(
                "A platform admin already exists. "
                "Bootstrap is disabled."
            )

        # 3. Hash password
        password_hash = hash_password(password)

        # 4. Prepare admin document
        admin_data = {
            "full_name": full_name,
            "email": email,
            "password_hash": password_hash,
            "role": "super_admin",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # 5. Save admin
        admin = await self.repository.create(admin_data)

        # 6. Return safe response
        return {
            "id": str(admin["_id"]),
            "full_name": admin["full_name"],
            "email": admin["email"],
            "role": admin["role"],
            "status": admin["status"]
        }
