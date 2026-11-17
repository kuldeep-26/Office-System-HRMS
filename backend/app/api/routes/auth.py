from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pymongo.errors import PyMongoError

from app.db.dependencies import get_database

from app.schemas.auth import (
    LoginRequest,
    LoginResponse
)

from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InactiveAccountError
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK
)
async def login(
    login_data: LoginRequest,
    db=Depends(get_database)
):

    service = AuthService(db)

    try:

        result = await service.login(
            organization_id=login_data.organization_id,
            email=str(login_data.email).lower(),
            password=login_data.password
        )

        return result

    except InvalidCredentialsError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    except InactiveAccountError:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive"
        )

    except PyMongoError:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )
