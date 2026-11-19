
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.designation_repository import DesignationRepository


class DesignationService:

    def __init__(self, db):
        self.db = db
        self.repository = DesignationRepository(db)

    async def _validate_organization(self, organization_id):

        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise ValueError("Organization not found or inactive")

    async def _validate_department(self, organization_id, department_id):

        if department_id is None:
            return

        if not ObjectId.is_valid(department_id):
            raise ValueError("Invalid department ID")

        department = await self.db.departments.find_one({
            "_id": ObjectId(department_id),
            "organization_id": ObjectId(organization_id)
        })

        if not department:
            raise ValueError(
                "Department not found in this organization"
            )

        if department.get("status") != "active":
            raise ValueError("Department is inactive")

    async def _check_duplicate_name(
        self,
        organization_id,
        designation_name,
        exclude_id=None
    ):

        query = {
            "organization_id": ObjectId(organization_id),
            "normalized_name": designation_name.strip().casefold()
        }

        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}

        existing = await self.db.designations.find_one(query)

        if existing:
            raise ValueError("Designation name already exists")

    @staticmethod
    def _serialize(designation):

        if not designation:
            return None

        designation["id"] = str(designation.pop("_id"))
        designation["organization_id"] = str(
            designation["organization_id"]
        )

        if designation.get("department_id") is not None:
            designation["department_id"] = str(
                designation["department_id"]
            )

        return designation

    async def create_designation(self, organization_id, designation_data):

        await self._validate_organization(organization_id)

        await self._validate_department(
            organization_id,
            designation_data.get("department_id")
        )

        await self._check_duplicate_name(
            organization_id,
            designation_data["designation_name"]
        )

        try:
            designation = await self.repository.create(
                organization_id,
                designation_data
            )

            return self._serialize(designation)

        except DuplicateKeyError:
            raise ValueError("Designation name already exists")

    async def get_designation(self, organization_id, designation_id):

        await self._validate_organization(organization_id)

        designation = await self.repository.get_by_id(
            organization_id,
            designation_id
        )

        return self._serialize(designation)

    async def get_all_designations(
        self,
        organization_id,
        skip=0,
        limit=20
    ):

        await self._validate_organization(organization_id)

        designations = await self.repository.get_all(
            organization_id,
            skip,
            limit
        )

        return [
            self._serialize(designation)
            for designation in designations
        ]

    async def update_designation(
        self,
        organization_id,
        designation_id,
        update_data
    ):

        await self._validate_organization(organization_id)

        existing = await self.repository.get_by_id(
            organization_id,
            designation_id
        )

        if not existing:
            return None

        if "department_id" in update_data:
            await self._validate_department(
                organization_id,
                update_data["department_id"]
            )

        if "designation_name" in update_data:
            await self._check_duplicate_name(
                organization_id,
                update_data["designation_name"],
                exclude_id=designation_id
            )

        try:
            designation = await self.repository.update(
                organization_id,
                designation_id,
                update_data
            )

            return self._serialize(designation)

        except DuplicateKeyError:
            raise ValueError("Designation name already exists")

    async def update_designation_status(
        self,
        organization_id,
        designation_id,
        new_status
    ):

        await self._validate_organization(organization_id)

        designation = await self.repository.update_status(
            organization_id,
            designation_id,
            new_status
        )

        return self._serialize(designation)
