
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class EmployeeAccountCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    initial_password: str = Field(
        min_length=12,
        max_length=128
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Full name cannot be empty")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).strip().lower()


class EmployeeAccountResponse(BaseModel):

    id: str
    organization_id: str
    employee_id: str
    full_name: str
    email: EmailStr
    role: str
    status: str
