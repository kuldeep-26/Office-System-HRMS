
from app.repositories.platform_admin_repository import (
    PlatformAdminRepository
)

from app.core.security import (
    verify_password,
    create_platform_access_token
)


class InvalidPlatformCredentialsError(Exception):
    pass


class InactivePlatformAdminError(Exception):
    pass


class PlatformAdminAuthService:

    def __init__(self, db):
        self.repository = PlatformAdminRepository(db)

    async def login(
        self,
        email: str,
        password: str
    ) -> dict:

        # 1. Normalize email
        email = email.strip().lower()

        # 2. Find platform admin
        admin = await self.repository.get_by_email(email)

        if not admin:
            raise InvalidPlatformCredentialsError()

        # 3. Verify password
        if not verify_password(
            password,
            admin["password_hash"]
        ):
            raise InvalidPlatformCredentialsError()

        # 4. Check account status
        if admin.get("status") != "active":
            raise InactivePlatformAdminError()

        # 5. Generate platform access token
        access_token = create_platform_access_token(
            admin_id=str(admin["_id"])
        )

        # 6. Update last login
        await self.repository.update_last_login(
            str(admin["_id"])
        )

        # 7. Return safe response
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "admin": {
                "id": str(admin["_id"]),
                "full_name": admin["full_name"],
                "email": admin["email"],
                "role": admin["role"],
                "status": admin["status"]
            }
        }
