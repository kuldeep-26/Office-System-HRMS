
import os
import uuid

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

FACE_STORAGE = (
    PROJECT_ROOT / "private_uploads" / "face_enrollments"
)


# --------------------------------------------------
# UPLOAD CONFIGURATION
# --------------------------------------------------

MAX_FACE_SIZE = 5 * 1024 * 1024

MAX_IMAGE_PIXELS = 12_000_000

ALLOWED_FACE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png"
}


# --------------------------------------------------
# ENCRYPTION
# --------------------------------------------------

def get_face_cipher():

    encryption_key = settings.FACE_ENCRYPTION_KEY

    if not encryption_key:
        raise HTTPException(
            status_code=500,
            detail="Face encryption is not configured"
        )

    try:
        return Fernet(encryption_key.encode("utf-8"))

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="Invalid face encryption configuration"
        )


# --------------------------------------------------
# IMAGE VALIDATION AND NORMALIZATION
# --------------------------------------------------

def normalize_face_image(content: bytes) -> bytes:
    """
    Validate the uploaded image and re-encode it
    as JPEG to remove unnecessary metadata.
    """

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

    try:
        with Image.open(BytesIO(content)) as image:

            if image.format not in {"JPEG", "PNG"}:
                raise HTTPException(
                    status_code=400,
                    detail="Only JPEG and PNG images are allowed"
                )

            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=400,
                    detail="Image dimensions are too large"
                )

            image.verify()

        # Reopen after verify because verify invalidates
        # the original image object.
        with Image.open(BytesIO(content)) as image:

            image = ImageOps.exif_transpose(image)

            image = image.convert("RGB")

            output = BytesIO()

            image.save(
                output,
                format="JPEG",
                quality=90,
                optimize=True
            )

            return output.getvalue()

    except HTTPException:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        ValueError
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unsupported image"
        )


# --------------------------------------------------
# SAVE ENCRYPTED FACE PHOTO
# --------------------------------------------------

async def save_face_photo(file: UploadFile):

    try:
        original_filename = Path(file.filename or "").name

        if not original_filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )

        extension = Path(original_filename).suffix.lower()

        if extension not in ALLOWED_FACE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, JPEG and PNG images are allowed"
            )

        if file.content_type != ALLOWED_FACE_TYPES[extension]:
            raise HTTPException(
                status_code=400,
                detail="Invalid image content type"
            )

        content = await file.read(MAX_FACE_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty"
            )

        if len(content) > MAX_FACE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Face photo exceeds the 5 MB limit"
            )

        # Validate and normalize image
        normalized_image = normalize_face_image(content)

        # Encrypt normalized image
        cipher = get_face_cipher()

        encrypted_content = cipher.encrypt(normalized_image)

        # Generate random storage filename
        stored_filename = f"{uuid.uuid4().hex}.enc"

        FACE_STORAGE.mkdir(
            parents=True,
            exist_ok=True
        )

        file_path = FACE_STORAGE / stored_filename

        try:
            with open(file_path, "xb") as destination:
                destination.write(encrypted_content)

        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Unable to save encrypted face photo"
            )

        return {
            "stored_filename": stored_filename,
            "storage_path": str(file_path),
            "content_type": "image/jpeg",
            "file_size": len(encrypted_content)
        }

    finally:
        await file.close()


# --------------------------------------------------
# GET ENCRYPTED FACE PHOTO
# --------------------------------------------------

def get_face_photo(stored_filename: str) -> bytes:
    """
    Read and decrypt a stored face photo.
    """

    if (
        not stored_filename
        or Path(stored_filename).name != stored_filename
        or not stored_filename.endswith(".enc")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid face photo filename"
        )

    file_path = (FACE_STORAGE / stored_filename).resolve()

    if file_path.parent != FACE_STORAGE.resolve():
        raise HTTPException(
            status_code=400,
            detail="Invalid face photo path"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Face photo not found"
        )

    try:
        encrypted_content = file_path.read_bytes()

        cipher = get_face_cipher()

        return cipher.decrypt(encrypted_content)

    except InvalidToken:
        raise HTTPException(
            status_code=500,
            detail="Unable to decrypt face photo"
        )

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Unable to read face photo"
        )


# --------------------------------------------------
# DELETE FACE PHOTO
# --------------------------------------------------

def delete_face_photo(stored_filename: str):

    if (
        not stored_filename
        or Path(stored_filename).name != stored_filename
        or not stored_filename.endswith(".enc")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid face photo filename"
        )

    file_path = (FACE_STORAGE / stored_filename).resolve()

    if file_path.parent != FACE_STORAGE.resolve():
        raise HTTPException(
            status_code=400,
            detail="Invalid face photo path"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Face photo not found"
        )

    try:
        os.remove(file_path)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Unable to delete face photo"
        )
