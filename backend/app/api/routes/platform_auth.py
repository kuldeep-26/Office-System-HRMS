
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.db.dependencies import get_database

from app.schemas.platform_admin_auth import (
    PlatformAdminLoginRequest,
    PlatformAdminLoginResponse
)

from app.services.platform_admin_auth_service import (
    PlatformAdminAuthService,
    InvalidPlatformCredentialsError,
    InactivePlatformAdminError
)


router = APIRouter(
    prefix="/platform-auth",
    tags=["Platform Authentication"]
)


@router.post(
    "/login",
    response_model=PlatformAdminLoginResponse
)
async def platform_admin_login(
    request: PlatformAdminLoginRequest,
    db=Depends(get_database)
):

    service = PlatformAdminAuthService(db)

    try:
        return await service.login(
            email=request.email,
            password=request.password
        )

    except InvalidPlatformCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    except InactivePlatformAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin account is inactive"
        )

    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
