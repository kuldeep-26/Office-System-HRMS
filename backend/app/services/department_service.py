
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.department_repository import DepartmentRepository


class DepartmentService:

    def __init__(self, db):
        self.db = db
        self.repository = DepartmentRepository(db)

    async def _validate_organization(self, organization_id):

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise ValueError("Organization not found or inactive")

    async def _check_duplicate_name(
        self,
        organization_id,
        department_name,
        exclude_id=None
    ):
        query = {
            "organization_id": ObjectId(organization_id),
            "normalized_name": department_name.strip().casefold()
        }

        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}

        existing = await self.db.departments.find_one(query)

        if existing:
            raise ValueError("Department name already exists")


    @staticmethod
    def _serialize(department):

        if not department:
            return None

        department["id"] = str(department.pop("_id"))
        department["organization_id"] = str(
            department["organization_id"]
        )

        return department

    async def create_department(self, organization_id, department_data):

        await self._validate_organization(organization_id)

        await self._check_duplicate_name(
            organization_id,
            department_data["department_name"]
        )

        try:
            department = await self.repository.create(
                organization_id,
                department_data
            )

            return self._serialize(department)

        except DuplicateKeyError:
            raise ValueError("Department name already exists")

    async def get_department(self, organization_id, department_id):

        await self._validate_organization(organization_id)

        department = await self.repository.get_by_id(
            organization_id,
            department_id
        )

        return self._serialize(department)

    async def get_all_departments(
        self,
        organization_id,
        skip=0,
        limit=20
    ):

        await self._validate_organization(organization_id)

        departments = await self.repository.get_all(
            organization_id,
            skip,
            limit
        )

        return [
            self._serialize(department)
            for department in departments
        ]

    async def update_department(
        self,
        organization_id,
        department_id,
        update_data
    ):

        await self._validate_organization(organization_id)

        existing = await self.repository.get_by_id(
            organization_id,
            department_id
        )

        if not existing:
            return None

        if "department_name" in update_data:
            await self._check_duplicate_name(
                organization_id,
                update_data["department_name"],
                exclude_id=department_id
            )

        try:
            department = await self.repository.update(
                organization_id,
                department_id,
                update_data
            )

            return self._serialize(department)

        except DuplicateKeyError:
            raise ValueError("Department name already exists")

    async def update_department_status(
        self,
        organization_id,
        department_id,
        new_status
    ):

        await self._validate_organization(organization_id)

        department = await self.repository.update_status(
            organization_id,
            department_id,
            new_status
        )

        return self._serialize(department)
