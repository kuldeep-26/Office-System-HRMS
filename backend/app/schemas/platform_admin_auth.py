
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class PlatformAdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class PlatformAdminResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    status: str


class PlatformAdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: PlatformAdminResponse
