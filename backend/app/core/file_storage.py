
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile


# Project root: Office-System-HRMS
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Private document storage directory
DOCUMENT_STORAGE = PROJECT_ROOT / "private_uploads" / "documents"

# Maximum upload size: 5 MB
MAX_FILE_SIZE = 5 * 1024 * 1024

# Allowed file extensions and MIME types
ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
}


async def save_uploaded_file(file: UploadFile):
    """
    Validate and save an uploaded document
    in private storage.
    """

    original_filename = Path(file.filename or "").name

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension"
        )

    if file.content_type not in ALLOWED_FILE_TYPES[extension]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file content type"
        )

    # Read at most 5 MB + 1 byte to detect oversized uploads
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds the 5 MB limit"
        )

    # Generate a unique internal filename
    stored_filename = f"{uuid.uuid4().hex}{extension}"

    DOCUMENT_STORAGE.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = DOCUMENT_STORAGE / stored_filename

    try:
        with open(file_path, "xb") as destination:
            destination.write(content)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Unable to save uploaded document"
        )

    finally:
        await file.close()

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "storage_path": str(file_path),
        "content_type": file.content_type,
        "file_size": len(content)
    }


def get_document_path(stored_filename: str) -> Path:
    """
    Resolve a stored document safely.
    """

    # Only allow generated UUID filenames
    if not stored_filename or Path(stored_filename).name != stored_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid stored filename"
        )

    file_path = (DOCUMENT_STORAGE / stored_filename).resolve()

    if file_path.parent != DOCUMENT_STORAGE.resolve():
        raise HTTPException(
            status_code=400,
            detail="Invalid document path"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found"
        )

    return file_path


def delete_stored_file(stored_filename: str):
    """
    Delete a document from private storage.
    """

    file_path = get_document_path(stored_filename)

    try:
        os.remove(file_path)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Unable to delete document file"
        )
