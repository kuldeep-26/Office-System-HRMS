
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepartmentCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    department_name: str = Field(
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )

    @field_validator("department_name")
    @classmethod
    def validate_department_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Department name cannot be empty")

        return value


class DepartmentUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    department_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )

    @field_validator("department_name")
    @classmethod
    def validate_department_name(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Department name cannot be empty")

        return value


class DepartmentStatusUpdate(BaseModel):

    status: Literal["active", "inactive"]


class DepartmentResponse(BaseModel):

    id: str
    organization_id: str
    department_name: str
    description: str | None = None
    status: str
