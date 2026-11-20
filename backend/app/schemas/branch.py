
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BranchCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    branch_name: str = Field(
        min_length=2,
        max_length=100
    )

    address: str | None = Field(
        default=None,
        max_length=500
    )

    city: str | None = Field(
        default=None,
        max_length=100
    )

    state: str | None = Field(
        default=None,
        max_length=100
    )

    country: str | None = Field(
        default=None,
        max_length=100
    )

    postal_code: str | None = Field(
        default=None,
        max_length=20
    )

    @field_validator("branch_name")
    @classmethod
    def validate_branch_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Branch name cannot be empty")

        return value


class BranchUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    branch_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)

    @field_validator("branch_name")
    @classmethod
    def validate_branch_name(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Branch name cannot be empty")

        return value


class BranchStatusUpdate(BaseModel):

    status: Literal["active", "inactive"]


class BranchResponse(BaseModel):

    id: str
    organization_id: str
    branch_name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    status: str
