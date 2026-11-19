
from typing import Literal

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator
)


class DesignationCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    designation_name: str = Field(
        min_length=2,
        max_length=100
    )

    department_id: str | None = None

    description: str | None = Field(
        default=None,
        max_length=500
    )

    @field_validator("designation_name")
    @classmethod
    def validate_designation_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Designation name cannot be empty")

        return value

    @field_validator("department_id")
    @classmethod
    def validate_department_id(cls, value):
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError("Invalid department ID")

        return value


class DesignationUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    designation_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    department_id: str | None = None

    description: str | None = Field(
        default=None,
        max_length=500
    )

    @field_validator("designation_name")
    @classmethod
    def validate_designation_name(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Designation name cannot be empty")

        return value

    @field_validator("department_id")
    @classmethod
    def validate_department_id(cls, value):
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError("Invalid department ID")

        return value


class DesignationStatusUpdate(BaseModel):

    status: Literal["active", "inactive"]


class DesignationResponse(BaseModel):

    id: str
    organization_id: str
    designation_name: str
    department_id: str | None = None
    description: str | None = None
    status: str
