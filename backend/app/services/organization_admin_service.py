from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.security import hash_password
from app.repositories.user_repository import UserRepository


class OrganizationAdminService:

    def __init__(self, db):
        self.db = db
        self.user_repository = UserRepository(db)

    async def create_admin(
        self,
        organization_id: str,
        full_name: str,
        email: str,
        password: str
    ) -> dict:

        # 1. Validate organization ID
        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        org_id = ObjectId(organization_id)

        # 2. Check organization existence
        organization = await self.db.organizations.find_one({
            "_id": org_id
        })

        if not organization:
            raise ValueError("Organization not found")

        # 3. Check organization status
        if organization.get("status") != "active":
            raise ValueError("Organization is inactive")

        # 4. Validate user information
        full_name = full_name.strip()
        email = email.strip().lower()

        if not full_name:
            raise ValueError("Full name is required")

        if not email:
            raise ValueError("Email is required")

        if len(password) < 10:
            raise ValueError(
                "Password must contain at least 10 characters"
            )

        # 5. Check duplicate email within organization
        existing_user = await self.user_repository.get_by_email(
            organization_id,
            email
        )

        if existing_user:
            raise ValueError(
                "Email already exists in this organization"
            )

        # 6. Retrieve Organization Admin role

        role = await self.db.roles.find_one({
            "scope": "organization",
            "name": "org_admin",
            "is_system": True
        })

        if not role:
            raise RuntimeError(
                "Organization Admin role not found"
            )


        # 7. Prepare user document
        user_data = {
            "organization_id": org_id,
            "full_name": full_name,
            "email": email,
            "password_hash": hash_password(password),
            "role_ids": [role["_id"]],
            "employee_id": None,
            "status": "active"
        }

        # 8. Insert user
        try:
            user = await self.user_repository.create(user_data)

        except DuplicateKeyError:
            raise ValueError(
                "Email already exists in this organization"
            )

        # 9. Return safe response
        return {
            "id": str(user["_id"]),
            "organization_id": str(user["organization_id"]),
            "full_name": user["full_name"],
            "email": user["email"],
            "role_ids": [
                str(role_id)
                for role_id in user["role_ids"]
            ],
            "status": user["status"]
        }
