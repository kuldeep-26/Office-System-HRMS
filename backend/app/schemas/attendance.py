
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AttendanceActionCreate(BaseModel):
    """
    Request schema for employee check-in or check-out.
    """

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(
        min_length=10,
        max_length=100
    )


class AttendanceResponse(BaseModel):
    """
    Response schema for an attendance event.
    """

    id: str
    organization_id: str
    employee_id: str
    session_id: str

    event_type: Literal[
        "check_in",
        "check_out"
    ]

    event_time: str

    source: Literal[
        "web",
        "mobile",
        "admin"
    ]

    created_at: str
