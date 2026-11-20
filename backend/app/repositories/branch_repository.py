
from datetime import datetime, timezone
from bson import ObjectId


class BranchRepository:

    def __init__(self, db):
        self.collection = db.branches

    async def create(self, organization_id, branch_data):

        org_id = ObjectId(organization_id)

        data = branch_data.copy()
        data["organization_id"] = org_id

        data["normalized_name"] = (
            data["branch_name"].strip().casefold()
        )

        now = datetime.now(timezone.utc)

        data["status"] = "active"
        data["created_at"] = now
        data["updated_at"] = now

        result = await self.collection.insert_one(data)

        return await self.get_by_id(
            organization_id,
            str(result.inserted_id)
        )

    async def get_by_id(self, organization_id, branch_id):

        if not ObjectId.is_valid(branch_id):
            return None

        return await self.collection.find_one({
            "_id": ObjectId(branch_id),
            "organization_id": ObjectId(organization_id)
        })

    async def get_all(self, organization_id, skip=0, limit=20):

        cursor = self.collection.find({
            "organization_id": ObjectId(organization_id)
        })

        cursor = cursor.sort("created_at", -1)

        return await cursor.skip(skip).limit(limit).to_list(
            length=limit
        )

    async def update(self, organization_id, branch_id, update_data):

        if not ObjectId.is_valid(branch_id):
            return None

        data = update_data.copy()

        if "branch_name" in data:
            data["normalized_name"] = (
                data["branch_name"].strip().casefold()
            )

        data["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.update_one(
            {
                "_id": ObjectId(branch_id),
                "organization_id": ObjectId(organization_id)
            },
            {
                "$set": data
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            branch_id
        )

    async def update_status(
        self,
        organization_id,
        branch_id,
        new_status
    ):

        if not ObjectId.is_valid(branch_id):
            return None

        result = await self.collection.update_one(
            {
                "_id": ObjectId(branch_id),
                "organization_id": ObjectId(organization_id)
            },
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            branch_id
        )
