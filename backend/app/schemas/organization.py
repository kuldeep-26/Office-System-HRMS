import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal

class OrganizationCreate(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    slug: str = Field(
        min_length=3,
        max_length=50
    )

    timezone: str = Field(
        default="Asia/Kolkata"
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):

        value = value.strip()

        if not value:
            raise ValueError("Organization name cannot be empty")

        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value):

        value = value.strip().lower()

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Slug must contain lowercase letters, numbers and hyphens"
            )

        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value):

        value = value.upper()

        if not value.isalpha():
            raise ValueError("Currency must contain alphabetic characters only")

        return value


class OrganizationResponse(BaseModel):

    id: str
    name: str
    slug: str
    timezone: str
    currency: str
    status: Literal["active", "inactive"]

    model_config = ConfigDict(from_attributes=True)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=3, max_length=50)
    timezone: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            raise ValueError("Name cannot be null")

        value = value.strip()

        if not value:
            raise ValueError("Organization name cannot be empty")

        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value):
        if value is None:
            raise ValueError("Slug cannot be null")

        value = value.strip().lower()

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("Slug must contain lowercase letters, numbers and hyphens")

        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        if value is None or not value.strip():
            raise ValueError("Timezone cannot be empty")

        return value.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value):
        if value is None:
            raise ValueError("Currency cannot be null")

        value = value.upper()

        if not value.isalpha():
            raise ValueError("Currency must contain alphabetic characters only")

        return value


class OrganizationStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]