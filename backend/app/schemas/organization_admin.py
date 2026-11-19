
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class OrganizationAdminCreateRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class OrganizationAdminResponse(BaseModel):

    id: str
    organization_id: str
    full_name: str
    email: EmailStr
    role_ids: list[str]
    status: str
