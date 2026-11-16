from app.core.security import (
    verify_password,
    create_access_token
)

from app.repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""
    pass


class InactiveAccountError(Exception):
    """Raised when the user account is inactive."""
    pass


class AuthService:

    def __init__(self, db):
        self.user_repository = UserRepository(db)

    # -----------------------------------------
    # USER LOGIN
    # -----------------------------------------

    async def login(
        self,
        organization_id: str,
        email: str,
        password: str
    ) -> dict:

        # 1. Find user within the specified organization
        user = await self.user_repository.get_by_email(
            organization_id=organization_id,
            email=email.strip().lower()
        )

        # 2. Reject invalid credentials
        if not user:
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        # 3. Verify password
        password_hash = user.get("password_hash")

        if not password_hash or not verify_password(
            password,
            password_hash
        ):
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        # 4. Check account status
        if user.get("status") != "active":
            raise InactiveAccountError(
                "Your account is inactive"
            )

        # 5. Extract identifiers
        user_id = str(user["_id"])

        actual_organization_id = str(
            user["organization_id"]
        )

        # 6. Generate access token
        access_token = create_access_token(
            user_id=user_id,
            organization_id=actual_organization_id
        )

        # 7. Update last login
        await self.user_repository.update_last_login(
            user_id=user_id,
            organization_id=actual_organization_id
        )

        # 8. Prepare safe user response
        role_ids = [
            str(role_id)
            for role_id in user.get("role_ids", [])
        ]

        safe_user = {
            "id": user_id,
            "organization_id": actual_organization_id,
            "email": user["email"],
            "role_ids": role_ids,
            "employee_id": (
                str(user["employee_id"])
                if user.get("employee_id")
                else None
            ),
            "status": user["status"]
        }

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": safe_user
        }
