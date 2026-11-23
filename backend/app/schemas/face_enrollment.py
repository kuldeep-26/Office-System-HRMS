
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FaceEnrollmentConsentCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    consent_given: bool

    consent_version: str = Field(
        min_length=1,
        max_length=30
    )

    purpose: Literal["attendance_verification"] = (
        "attendance_verification"
    )


class FaceEnrollmentResponse(BaseModel):

    id: str
    organization_id: str
    employee_id: str

    consent_given: bool
    consent_version: str
    purpose: str

    enrollment_status: Literal[
        "consent_pending",
        "consented",
        "photo_uploaded",
        "enrolled",
        "rejected",
        "revoked"
    ]

    created_at: str
    updated_at: str
