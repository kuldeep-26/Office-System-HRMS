from bson import ObjectId

class OrganizationRepository:

    def __init__(self, db):
        self.collection = db.organizations

    async def create(self, organization_data: dict):

        result = await self.collection.insert_one(
            organization_data
        )

        return await self.collection.find_one(
            {"_id": result.inserted_id}
        )

    async def get_by_id(self, organization_id: str):

        if not ObjectId.is_valid(organization_id):
            return None

        return await self.collection.find_one(
            {"_id": ObjectId(organization_id)}
        )

    async def get_by_slug(self, slug: str):

        return await self.collection.find_one(
            {"slug": slug}
        )

    async def update(self, organization_id: str, update_data: dict):
        if not ObjectId.is_valid(organization_id):
            return None

        await self.collection.update_one(
            {"_id": ObjectId(organization_id)},
            {"$set": update_data}
        )

        return await self.get_by_id(organization_id)
