
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId


class EmployeeCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    employee_code: str = Field(
        min_length=2,
        max_length=30
    )

    user_id: str | None = None

    department_id: str | None = None

    designation_id: str | None = None

    branch_id: str | None = None

    @field_validator(
        "employee_code"
    )
    @classmethod
    def validate_employee_code(cls, value):

        value = value.strip()

        if not value:
            raise ValueError("Employee code cannot be empty")

        return value

    @field_validator(
        "user_id",
        "department_id",
        "designation_id",
        "branch_id"
    )
    @classmethod
    def validate_object_ids(cls, value):

        if value is None:
            return value

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid MongoDB ObjectId")

        return value


class EmployeeUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    employee_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=30
    )

    user_id: str | None = None

    department_id: str | None = None

    designation_id: str | None = None

    branch_id: str | None = None

    @field_validator("employee_code")
    @classmethod
    def validate_employee_code(cls, value):

        if value is None:
            raise ValueError("Employee code cannot be null")

        value = value.strip()

        if not value:
            raise ValueError("Employee code cannot be empty")

        return value

    @field_validator(
        "user_id",
        "department_id",
        "designation_id",
        "branch_id"
    )
    @classmethod
    def validate_object_ids(cls, value):

        if value is None:
            return value

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid MongoDB ObjectId")

        return value


class EmployeeStatusUpdate(BaseModel):

    status: Literal["active", "inactive"]


class EmployeeResponse(BaseModel):

    id: str
    organization_id: str
    employee_code: str
    user_id: str | None = None
    department_id: str | None = None
    designation_id: str | None = None
    branch_id: str | None = None
    status: str
