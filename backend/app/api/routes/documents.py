
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
    Query
)
from fastapi.responses import FileResponse

from app.db.dependencies import get_database
from app.services.document_service import DocumentService
from app.api.dependencies.permissions import require_permission


router = APIRouter(
    prefix="/documents",
    tags=["Employee Documents"]
)


# --------------------------------------------------
# UPLOAD EMPLOYEE DOCUMENT
# --------------------------------------------------

@router.post("/{employee_id}/upload")
async def upload_employee_document(
    employee_id: str,
    file: UploadFile = File(...),
    category: str = Form(...),
    description: str | None = Form(None),
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("document:upload")
    )
):

    allowed_categories = {
        "identity",
        "education",
        "employment",
        "tax",
        "other"
    }

    if category not in allowed_categories:
        raise HTTPException(
            status_code=400,
            detail="Invalid document category"
        )

    service = DocumentService(db)

    return await service.upload_document(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        uploaded_by=current_user["id"],
        file=file,
        category=category,
        description=description
    )


# --------------------------------------------------
# GET EMPLOYEE DOCUMENTS
# --------------------------------------------------

@router.get("/{employee_id}")
async def get_employee_documents(
    employee_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("document:read")
    )
):

    service = DocumentService(db)

    return await service.get_employee_documents(
        organization_id=current_user["organization_id"],
        employee_id=employee_id,
        skip=skip,
        limit=limit
    )


# --------------------------------------------------
# DOWNLOAD DOCUMENT
# --------------------------------------------------

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("document:read")
    )
):

    service = DocumentService(db)

    document, file_path = await service.get_download_file(
        organization_id=current_user["organization_id"],
        document_id=document_id
    )

    return FileResponse(
        path=file_path,
        filename=document["original_filename"],
        media_type=document["content_type"]
    )


# --------------------------------------------------
# DELETE DOCUMENT
# --------------------------------------------------

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db=Depends(get_database),
    current_user: dict = Depends(
        require_permission("document:delete")
    )
):

    service = DocumentService(db)

    return await service.delete_document(
        organization_id=current_user["organization_id"],
        document_id=document_id
    )
