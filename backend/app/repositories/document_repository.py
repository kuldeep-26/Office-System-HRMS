
from datetime import datetime, timezone

from bson import ObjectId


class DocumentRepository:

    def __init__(self, db):
        self.collection = db.documents

    # CREATE DOCUMENT METADATA
    async def create(self, document_data: dict):

        now = datetime.now(timezone.utc)

        document_data["created_at"] = now
        document_data["updated_at"] = now

        result = await self.collection.insert_one(document_data)

        return await self.get_by_id(
            str(document_data["organization_id"]),
            str(result.inserted_id)
        )

    # GET DOCUMENT BY ID
    async def get_by_id(
        self,
        organization_id: str,
        document_id: str
    ):

        if not ObjectId.is_valid(document_id):
            return None

        return await self.collection.find_one({
            "_id": ObjectId(document_id),
            "organization_id": ObjectId(organization_id)
        })

    # GET DOCUMENTS FOR AN EMPLOYEE
    async def get_by_employee(
        self,
        organization_id: str,
        employee_id: str,
        skip: int = 0,
        limit: int = 20
    ):

        cursor = self.collection.find({
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id)
        })

        cursor = cursor.sort("created_at", -1)

        return await cursor.skip(skip).limit(limit).to_list(
            length=limit
        )

    # COUNT EMPLOYEE DOCUMENTS
    async def count_by_employee(
        self,
        organization_id: str,
        employee_id: str
    ):

        return await self.collection.count_documents({
            "organization_id": ObjectId(organization_id),
            "employee_id": ObjectId(employee_id)
        })

    # DELETE DOCUMENT METADATA
    async def delete(
        self,
        organization_id: str,
        document_id: str
    ):

        if not ObjectId.is_valid(document_id):
            return False

        result = await self.collection.delete_one({
            "_id": ObjectId(document_id),
            "organization_id": ObjectId(organization_id)
        })

        return result.deleted_count > 0
