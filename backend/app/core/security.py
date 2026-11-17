from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from pwdlib import PasswordHash
from .config import settings

# --------------------------------------------------
# PASSWORD HASHING
# --------------------------------------------------

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using Argon2id.
    Never store the original password in MongoDB.
    """
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify a password against its stored hash.
    """
    return password_hasher.verify(
        plain_password,
        hashed_password
    )


# --------------------------------------------------
# JWT CONFIGURATION
# --------------------------------------------------

def get_jwt_secret() -> str:
    """
    Retrieve JWT secret from application settings.
    """
    secret = settings.JWT_SECRET_KEY

    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured"
        )

    return secret


# --------------------------------------------------
# ACCESS TOKEN GENERATION
# --------------------------------------------------

def create_access_token(
    user_id: str,
    organization_id: str,
    expires_delta: timedelta | None = None
) -> str:
    """
    Generate a signed JWT access token.
    """

    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_MINUTES
        )

    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "org_id": organization_id,
        "type": "access",
        "iat": now,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    token = jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm="HS256"
    )

    return token


# --------------------------------------------------
# ACCESS TOKEN VALIDATION
# --------------------------------------------------

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Validate JWT signature, algorithm,
    issuer, audience and expiration.
    """

    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=["HS256"],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        options={
            "require": [
                "exp",
                "iat",
                "sub",
                "iss",
                "aud",
                "org_id",
                "type"
            ]
        }
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError(
            "Invalid token type"
        )

    return payload



# --------------------------------------------------
# PLATFORM ADMIN ACCESS TOKEN
# --------------------------------------------------

def create_platform_access_token(
    admin_id: str,
    expires_delta: timedelta | None = None
) -> str:

    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_MINUTES
        )

    expire = now + expires_delta

    payload = {
        "sub": admin_id,
        "scope": "platform",
        "type": "platform_access",
        "iat": now,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm="HS256"
    )


# --------------------------------------------------
# PLATFORM ADMIN TOKEN VALIDATION
# --------------------------------------------------

def decode_platform_access_token(
    token: str
) -> dict[str, Any]:

    payload = jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=["HS256"],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        options={
            "require": [
                "exp",
                "iat",
                "sub",
                "iss",
                "aud",
                "scope",
                "type"
            ]
        }
    )

    if (
        payload.get("type") != "platform_access"
        or payload.get("scope") != "platform"
    ):
        raise jwt.InvalidTokenError(
            "Invalid platform access token"
        )

    return payload
