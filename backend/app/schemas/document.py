
from datetime import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


DocumentCategory = Literal[
    "identity",
    "education",
    "employment",
    "tax",
    "other"
]


class DocumentResponse(BaseModel):

    model_config = ConfigDict(extra="ignore")

    id: str
    organization_id: str
    employee_id: str

    original_filename: str
    stored_filename: str

    category: DocumentCategory
    description: str | None = None

    content_type: str
    file_size: int

    uploaded_by: str
    created_at: datetime


class DocumentListResponse(BaseModel):

    documents: list[DocumentResponse]
    total: int
