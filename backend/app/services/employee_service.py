
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.employee_repository import EmployeeRepository


class EmployeeService:

    def __init__(self, db):
        self.db = db
        self.repository = EmployeeRepository(db)

    async def _validate_organization(self, organization_id):
        if not ObjectId.is_valid(organization_id):
            raise ValueError("Invalid organization ID")

        organization = await self.db.organizations.find_one({
            "_id": ObjectId(organization_id),
            "status": "active"
        })

        if not organization:
            raise ValueError("Organization not found or inactive")

    async def _validate_references(self, organization_id, data):
        reference_collections = {
            "user_id": "users",
            "department_id": "departments",
            "designation_id": "designations",
            "branch_id": "branches"
        }

        for field, collection_name in reference_collections.items():
            reference_id = data.get(field)

            if reference_id is None:
                continue

            if not ObjectId.is_valid(reference_id):
                raise ValueError(f"Invalid {field}")

            query = {
                "_id": ObjectId(reference_id),
                "organization_id": ObjectId(organization_id)
            }

            document = await self.db[collection_name].find_one(query)

            if not document:
                raise ValueError(
                    f"Invalid {field}: record not found in this organization"
                )

            if document.get("status") != "active":
                raise ValueError(f"The linked {field} is inactive")

            if field == "user_id":
                existing_employee = await self.db.employees.find_one({
                    "organization_id": ObjectId(organization_id),
                    "user_id": ObjectId(reference_id)
                })

                if existing_employee:
                    raise ValueError(
                        "This user is already linked to an employee"
                    )

    @staticmethod
    def _serialize(employee):
        if not employee:
            return None

        for field in (
            "_id",
            "organization_id",
            "user_id",
            "department_id",
            "designation_id",
            "branch_id"
        ):
            if employee.get(field) is not None:
                employee[field] = str(employee[field])

        employee["id"] = employee.pop("_id")
        return employee

    async def create_employee(self, organization_id, employee_data):
        await self._validate_organization(organization_id)
        await self._validate_references(organization_id, employee_data)

        try:
            employee = await self.repository.create(
                organization_id,
                employee_data
            )
            return self._serialize(employee)

        except DuplicateKeyError:
            raise ValueError("Employee code already exists")

    async def get_employee(self, organization_id, employee_id):
        await self._validate_organization(organization_id)

        employee = await self.repository.get_by_id(
            organization_id,
            employee_id
        )

        return self._serialize(employee)

    async def get_all_employees(self, organization_id, skip=0, limit=20):
        await self._validate_organization(organization_id)

        employees = await self.repository.get_all(
            organization_id,
            skip,
            limit
        )

        return [self._serialize(employee) for employee in employees]

    async def update_employee(
        self,
        organization_id,
        employee_id,
        update_data
    ):
        await self._validate_organization(organization_id)

        existing = await self.repository.get_by_id(
            organization_id,
            employee_id
        )

        if not existing:
            return None

        await self._validate_references(
            organization_id,
            update_data
        )

        try:
            employee = await self.repository.update(
                organization_id,
                employee_id,
                update_data
            )
            return self._serialize(employee)

        except DuplicateKeyError:
            raise ValueError("Employee code already exists")

    async def update_employee_status(
        self,
        organization_id,
        employee_id,
        status
    ):
        await self._validate_organization(organization_id)

        employee = await self.repository.update_status(
            organization_id,
            employee_id,
            status
        )

        return self._serialize(employee)
