from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from bson import ObjectId

class LoginRequest(BaseModel):

    organization_id: str = Field(
        min_length=24,
        max_length=24
    )

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id(cls, value):

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid organization ID")

        return value


class AuthUserResponse(BaseModel):

    id: str
    organization_id: str
    email: EmailStr
    role_ids: list[str] = Field(default_factory=list)
    employee_id: str | None = None
    status: str


class LoginResponse(BaseModel):

    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
