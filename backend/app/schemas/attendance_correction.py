
from datetime import date, datetime
from typing import Literal

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator
)


CorrectionType = Literal[
    "missing_check_in",
    "missing_check_out",
    "adjust_check_in",
    "adjust_check_out"
]


CorrectionStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "applied"
]


class AttendanceCorrectionCreate(BaseModel):
    """
    Schema for an employee submitting an attendance correction request.
    """

    model_config = ConfigDict(extra="forbid")

    correction_type: CorrectionType

    attendance_date: date

    original_event_id: str | None = None

    proposed_event_time: datetime

    reason: str = Field(
        min_length=10,
        max_length=500
    )

    @field_validator("original_event_id")
    @classmethod
    def validate_original_event_id(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not ObjectId.is_valid(value):
            raise ValueError("Invalid attendance event ID")

        return value

    @field_validator("proposed_event_time")
    @classmethod
    def validate_proposed_event_time(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Proposed event time must include a timezone"
            )

        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value):
        value = value.strip()

        if len(value) < 10:
            raise ValueError(
                "Correction reason must contain at least 10 characters"
            )

        return value

    @model_validator(mode="after")
    def validate_correction_reference(self):
        adjustment_types = {
            "adjust_check_in",
            "adjust_check_out"
        }

        missing_event_types = {
            "missing_check_in",
            "missing_check_out"
        }

        if (
            self.correction_type in adjustment_types
            and self.original_event_id is None
        ):
            raise ValueError(
                "Original attendance event ID is required "
                "for adjustment requests"
            )

        if (
            self.correction_type in missing_event_types
            and self.original_event_id is not None
        ):
            raise ValueError(
                "Original attendance event ID must not be provided "
                "for missing event requests"
            )

        return self


class AttendanceCorrectionReview(BaseModel):
    """
    Schema for HR approving or rejecting a correction request.
    """

    model_config = ConfigDict(extra="forbid")

    review_reason: str = Field(
        min_length=5,
        max_length=500
    )

    @field_validator("review_reason")
    @classmethod
    def validate_review_reason(cls, value):
        value = value.strip()

        if len(value) < 5:
            raise ValueError(
                "Review reason must contain at least 5 characters"
            )

        return value


class AttendanceCorrectionResponse(BaseModel):
    """
    Response schema for an attendance correction request.
    """

    id: str

    organization_id: str

    employee_id: str

    correction_type: CorrectionType

    attendance_date: str

    original_event_id: str | None = None

    proposed_event_time: str

    reason: str

    status: CorrectionStatus

    created_by_user_id: str

    reviewed_by_user_id: str | None = None

    reviewed_at: str | None = None

    review_reason: str | None = None

    applied_at: str | None = None

    applied_event_id: str | None = None

    created_at: str

    updated_at: str
