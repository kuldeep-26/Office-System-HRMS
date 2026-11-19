
from datetime import datetime, timezone
from bson import ObjectId


class EmployeeRepository:

    def __init__(self, db):
        self.collection = db.employees

    # CREATE EMPLOYEE
    async def create(self, organization_id: str, employee_data: dict):

        org_id = ObjectId(organization_id)

        data = employee_data.copy()

        data["organization_id"] = org_id

        for field in (
            "user_id",
            "department_id",
            "designation_id",
            "branch_id"
        ):
            value = data.get(field)

            if value is not None:
                data[field] = ObjectId(value)

        now = datetime.now(timezone.utc)

        data["status"] = "active"
        data["created_at"] = now
        data["updated_at"] = now

        result = await self.collection.insert_one(data)

        return await self.get_by_id(
            organization_id,
            str(result.inserted_id)
        )

    # GET EMPLOYEE BY ID
    async def get_by_id(
        self,
        organization_id: str,
        employee_id: str
    ):

        if not ObjectId.is_valid(employee_id):
            return None

        return await self.collection.find_one({
            "_id": ObjectId(employee_id),
            "organization_id": ObjectId(organization_id)
        })

    # GET ALL EMPLOYEES
    async def get_all(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 20
    ):

        cursor = self.collection.find({
            "organization_id": ObjectId(organization_id)
        })

        cursor = cursor.sort("created_at", -1)

        return await cursor.skip(skip).limit(limit).to_list(
            length=limit
        )

    # UPDATE EMPLOYEE
    async def update(
        self,
        organization_id: str,
        employee_id: str,
        update_data: dict
    ):

        if not ObjectId.is_valid(employee_id):
            return None

        data = update_data.copy()

        for field in (
            "user_id",
            "department_id",
            "designation_id",
            "branch_id"
        ):
            value = data.get(field)

            if value is not None:
                data[field] = ObjectId(value)

        data["updated_at"] = datetime.now(timezone.utc)

        result = await self.collection.update_one(
            {
                "_id": ObjectId(employee_id),
                "organization_id": ObjectId(organization_id)
            },
            {"$set": data}
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(
            organization_id,
            employee_id
        )

    # UPDATE EMPLOYEE STATUS
    async def update_status(
        self,
        organization_id: str,
        employee_id: str,
        new_status: str
    ):

        if not ObjectId.is_valid(employee_id):
            return None

        result = await self.collection.update_one(
            {
                "_id": ObjectId(employee_id),
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
            employee_id
        )

    # DELETE EMPLOYEE
    async def delete(
        self,
        organization_id: str,
        employee_id: str
    ):

        if not ObjectId.is_valid(employee_id):
            return False

        result = await self.collection.delete_one({
            "_id": ObjectId(employee_id),
            "organization_id": ObjectId(organization_id)
        })

        return result.deleted_count > 0
