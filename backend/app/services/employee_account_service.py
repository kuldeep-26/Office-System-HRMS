
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.user_repository import UserRepository
from app.core.security import hash_password


class EmployeeAccountService:

    def __init__(self, db):
        self.db = db
        self.user_repository = UserRepository(db)

    async def create_employee_account(
        self,
        organization_id: str,
        employee_id: str,
        account_data: dict
    ):

        # 1. Validate IDs
        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        if not ObjectId.is_valid(employee_id):
            raise ValueError("Invalid employee ID")

        organization_object_id = ObjectId(organization_id)
        employee_object_id = ObjectId(employee_id)

        # 2. Verify organization is active
        organization = await self.db.organizations.find_one({
            "_id": organization_object_id,
            "status": "active"
        })

        if not organization:
            raise ValueError("Organization not found or inactive")

        # 3. Find employee within organization
        employee = await self.db.employees.find_one({
            "_id": employee_object_id,
            "organization_id": organization_object_id,
            "status": "active"
        })

        if not employee:
            raise ValueError(
                "Active employee not found in this organization"
            )

        # 4. Check whether employee already has a login
        if employee.get("user_id"):
            raise ValueError(
                "This employee already has a login account"
            )

        # 5. Normalize email
        email = account_data["email"].strip().lower()

        # 6. Check duplicate email within organization
        existing_user = await self.user_repository.get_by_email(
            organization_id,
            email
        )

        if existing_user:
            raise ValueError(
                "This email is already registered in this organization"
            )

        # 7. Retrieve employee role
        employee_role = await self.db.roles.find_one({
            "scope": "organization",
            "name": "employee",
            "is_system": True
        })

        if not employee_role:
            raise ValueError(
                "Employee role not found. Initialize system roles first."
            )

        # 8. Hash initial password
        password_hash = hash_password(
            account_data["initial_password"]
        )

        now = datetime.now(timezone.utc)

        # 9. Prepare user account
        user_data = {
            "organization_id": organization_object_id,
            "employee_id": employee_object_id,
            "full_name": account_data["full_name"].strip(),
            "email": email,
            "password_hash": password_hash,
            "role_ids": [employee_role["_id"]],
            "status": "active",
            "created_at": now,
            "updated_at": now
        }

        # 10. Create user and link employee
        try:
            user = await self.user_repository.create(user_data)

        except DuplicateKeyError:
            raise ValueError(
                "An account with this email already exists"
            )

        try:
            link_result = await self.db.employees.update_one(
                {
                    "_id": employee_object_id,
                    "organization_id": organization_object_id,
                    "user_id": None
                },
                {
                    "$set": {
                        "user_id": user["_id"],
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if link_result.modified_count != 1:
                raise ValueError(
                    "Employee account could not be linked. "
                    "The employee may already have an account."
                )

        except Exception:
            # Roll back the newly created user if linking fails
            await self.db.users.delete_one({
                "_id": user["_id"],
                "organization_id": organization_object_id
            })
            raise

        # 11. Return safe response
        return {
            "id": str(user["_id"]),
            "organization_id": str(organization_object_id),
            "employee_id": str(employee_object_id),
            "full_name": user["full_name"],
            "email": user["email"],
            "role": "employee",
            "status": user["status"]
        }
