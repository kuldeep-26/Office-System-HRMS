
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.core.security import decode_platform_access_token
from app.db.dependencies import get_database
from app.repositories.platform_admin_repository import (
    PlatformAdminRepository
)


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_platform_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db=Depends(get_database)
):
    # 1. Check whether Authorization header exists
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 2. Extract token
    token = credentials.credentials

    # 3. Validate platform JWT
    try:
        payload = decode_platform_access_token(token)

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 4. Extract admin ID
    admin_id = payload.get("sub")

    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid platform token"
        )

    # 5. Retrieve admin from database
    repository = PlatformAdminRepository(db)

    admin = await repository.get_by_id(admin_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform admin not found"
        )

    # 6. Check account status
    if admin.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin account is inactive"
        )

    # 7. Return safe admin information
    return {
        "id": str(admin["_id"]),
        "full_name": admin["full_name"],
        "email": admin["email"],
        "role": admin["role"],
        "status": admin["status"]
    }
