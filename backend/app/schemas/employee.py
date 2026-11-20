
from datetime import date
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, field_validator


GenderType = Literal[
    "male",
    "female",
    "non_binary",
    "prefer_not_to_say",
    "other"
]

EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "intern"
]


class EmployeeCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    # Existing employee fields
    employee_code: str = Field(min_length=2, max_length=30)
    user_id: str | None = None
    department_id: str | None = None
    designation_id: str | None = None
    branch_id: str | None = None

    # Personal profile fields
    date_of_birth: date | None = None
    gender: GenderType | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)

    # Employment fields
    joining_date: date | None = None
    employment_type: EmploymentType | None = None
    reporting_manager_id: str | None = None

    @field_validator("employee_code")
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
        "branch_id",
        "reporting_manager_id"
    )
    @classmethod
    def validate_object_ids(cls, value):
        if value is None:
            return value

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid MongoDB ObjectId")

        return value

    @field_validator(
        "phone_number",
        "address",
        "emergency_contact_name",
        "emergency_contact_phone"
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return value

        value = value.strip()

        return value or None


class EmployeeUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    # Existing employee fields
    employee_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=30
    )

    user_id: str | None = None
    department_id: str | None = None
    designation_id: str | None = None
    branch_id: str | None = None

    # Personal profile fields
    date_of_birth: date | None = None
    gender: GenderType | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)

    # Employment fields
    joining_date: date | None = None
    employment_type: EmploymentType | None = None
    reporting_manager_id: str | None = None

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
        "branch_id",
        "reporting_manager_id"
    )
    @classmethod
    def validate_object_ids(cls, value):
        if value is None:
            return value

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid MongoDB ObjectId")

        return value

    @field_validator(
        "phone_number",
        "address",
        "emergency_contact_name",
        "emergency_contact_phone"
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return value

        value = value.strip()

        return value or None


class EmployeeStatusUpdate(BaseModel):

    status: Literal["active", "inactive"]


class EmployeeResponse(BaseModel):

    id: str
    organization_id: str
    employee_code: str

    # Existing employee fields
    user_id: str | None = None
    department_id: str | None = None
    designation_id: str | None = None
    branch_id: str | None = None

    # Personal profile fields
    date_of_birth: date | None = None
    gender: GenderType | None = None
    phone_number: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    # Employment fields
    joining_date: date | None = None
    employment_type: EmploymentType | None = None
    reporting_manager_id: str | None = None

    status: str
