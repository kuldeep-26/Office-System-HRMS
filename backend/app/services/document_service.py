
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.repositories.document_repository import DocumentRepository
from app.core.file_storage import (
    save_uploaded_file,
    get_document_path,
    delete_stored_file
)


class DocumentService:

    def __init__(self, db):
        self.db = db
        self.repository = DocumentRepository(db)

    # VALIDATE ORGANIZATION
    async def _validate_organization(self, organization_id):

        if not ObjectId.is_valid(organization_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID"
            )

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise HTTPException(
                status_code=404,
                detail="Organization not found or inactive"
            )

    # VALIDATE EMPLOYEE
    async def _validate_employee(
        self,
        organization_id,
        employee_id
    ):

        if not ObjectId.is_valid(employee_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid employee ID"
            )

        employee = await self.db.employees.find_one({
            "_id": ObjectId(employee_id),
            "organization_id": ObjectId(organization_id),
            "status": "active"
        })

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Active employee not found in this organization"
            )

        return employee

    # SERIALIZE DOCUMENT
    @staticmethod
    def _serialize(document):

        if not document:
            return None

        for field in (
            "_id",
            "organization_id",
            "employee_id",
            "uploaded_by"
        ):
            if document.get(field) is not None:
                document[field] = str(document[field])

        document["id"] = document.pop("_id")

        # Never expose the physical storage path in API responses
        document.pop("storage_path", None)

        return document

    # UPLOAD DOCUMENT
    async def upload_document(
        self,
        organization_id,
        employee_id,
        uploaded_by,
        file: UploadFile,
        category,
        description=None
    ):

        await self._validate_organization(organization_id)

        await self._validate_employee(
            organization_id,
            employee_id
        )

        if not ObjectId.is_valid(uploaded_by):
            raise HTTPException(
                status_code=401,
                detail="Invalid uploader ID"
            )

        # Save file in private storage
        file_info = await save_uploaded_file(file)

        document_data = {
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id),
            "uploaded_by": ObjectId(uploaded_by),

            "original_filename": file_info["original_filename"],
            "stored_filename": file_info["stored_filename"],
            "storage_path": file_info["storage_path"],

            "category": category,
            "description": description,

            "content_type": file_info["content_type"],
            "file_size": file_info["file_size"]
        }

        try:
            document = await self.repository.create(document_data)

            return self._serialize(document)

        except Exception:
            # Prevent orphaned files if MongoDB insertion fails
            try:
                delete_stored_file(file_info["stored_filename"])
            except Exception:
                pass

            raise

    # GET DOCUMENT
    async def get_document(
        self,
        organization_id,
        document_id
    ):

        await self._validate_organization(organization_id)

        document = await self.repository.get_by_id(
            organization_id,
            document_id
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        return document

    # LIST EMPLOYEE DOCUMENTS
    async def get_employee_documents(
        self,
        organization_id,
        employee_id,
        skip=0,
        limit=20
    ):

        await self._validate_organization(organization_id)

        await self._validate_employee(
            organization_id,
            employee_id
        )

        documents = await self.repository.get_by_employee(
            organization_id,
            employee_id,
            skip,
            limit
        )

        total = await self.repository.count_by_employee(
            organization_id,
            employee_id
        )

        return {
            "documents": [
                self._serialize(document)
                for document in documents
            ],
            "total": total
        }

    # GET PRIVATE FILE PATH
    async def get_download_file(
        self,
        organization_id,
        document_id
    ):

        document = await self.get_document(
            organization_id,
            document_id
        )

        file_path = get_document_path(
            document["stored_filename"]
        )

        return document, file_path

    # DELETE DOCUMENT
    async def delete_document(
        self,
        organization_id,
        document_id
    ):

        document = await self.get_document(
            organization_id,
            document_id
        )

        # Delete the physical file first.
        # Keep metadata if file deletion fails.
        delete_stored_file(document["stored_filename"])

        deleted = await self.repository.delete(
            organization_id,
            document_id
        )

        if not deleted:
            raise HTTPException(
                status_code=500,
                detail="Document metadata could not be deleted"
            )

        return {
            "message": "Document deleted successfully"
        }
