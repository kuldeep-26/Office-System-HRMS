from datetime import datetime, timezone


class RolePermissionService:

    def __init__(self, db):
        self.db = db

    async def assign_permissions(
        self,
        role_name: str,
        permission_keys: list[str]
    ):

        # 1. Find organization role
        role = await self.db.roles.find_one({
            "scope": "organization",
            "name": role_name
        })

        if not role:
            raise ValueError("Role not found")

        # 2. Remove duplicate permission keys
        permission_keys = list(set(permission_keys))

        # 3. Verify all requested permissions exist
        permissions = await self.db.permissions.find({
            "permission_key": {
                "$in": permission_keys
            }
        }).to_list(length=None)

        valid_keys = {
            permission["permission_key"]
            for permission in permissions
        }

        invalid_keys = set(permission_keys) - valid_keys

        if invalid_keys:
            raise ValueError(
                f"Invalid permissions: {sorted(invalid_keys)}"
            )

        # 4. Update role permissions
        await self.db.roles.update_one(
            {"_id": role["_id"]},
            {
                "$set": {
                    "permission_keys": permission_keys,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "role": role_name,
            "permission_count": len(permission_keys),
            "permission_keys": permission_keys
        }
