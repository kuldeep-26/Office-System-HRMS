
from bson import ObjectId

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from app.core.security import decode_access_token
from app.db.dependencies import get_database
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


# --------------------------------------------------
# GET CURRENT ORGANIZATION USER
# --------------------------------------------------

async def get_current_organization_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db=Depends(get_database)
):

    # 1. Check Authorization header
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    # 2. Validate JWT
    try:
        payload = decode_access_token(token)

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 3. Extract identifiers
    user_id = payload.get("sub")
    organization_id = payload.get("org_id")

    if (
        not user_id
        or not organization_id
        or not ObjectId.is_valid(user_id)
        or not ObjectId.is_valid(organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )

    # 4. Verify organization exists and is active
    organization = await db.organizations.find_one({
        "_id": ObjectId(organization_id)
    })

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization not found"
        )

    if organization.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )

    # 5. Retrieve user within token organization
    repository = UserRepository(db)

    user = await repository.get_by_id(
        user_id=user_id,
        organization_id=organization_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # 6. Check account status
    if user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # 7. Normalize assigned role IDs
    role_ids = []

    for role_id in user.get("role_ids", []):

        if isinstance(role_id, ObjectId):
            role_ids.append(role_id)

        elif ObjectId.is_valid(str(role_id)):
            role_ids.append(ObjectId(str(role_id)))

    # 8. Retrieve organization-scoped roles
    roles = []

    if role_ids:
        roles = await db.roles.find({
            "_id": {"$in": role_ids},
            "scope": "organization"
        }).to_list(length=None)

    # 9. Collect permissions from assigned roles
    permissions = set()

    for role in roles:
        permissions.update(
            role.get("permission_keys", [])
        )

    # 10. Return authenticated user context
    return {
        "id": str(user["_id"]),
        "organization_id": str(user["organization_id"]),
        "email": user["email"],
        "role_ids": [
            str(role_id)
            for role_id in user.get("role_ids", [])
        ],
        "permissions": permissions,
        "status": user["status"]
    }


# --------------------------------------------------
# REQUIRE PERMISSION
# --------------------------------------------------

def require_permission(permission_key: str):

    async def permission_checker(
        current_user: dict = Depends(
            get_current_organization_user
        )
    ):

        if permission_key not in current_user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return permission_checker
