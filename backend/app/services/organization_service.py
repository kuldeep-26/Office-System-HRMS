from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from app.repositories.organization_repository import (
    OrganizationRepository
)

class OrganizationService:

    def __init__(self, db):

        self.repository = OrganizationRepository(db)

    async def create_organization(self, organization_data: dict):

        organization_data["created_at"] = datetime.now(timezone.utc)

        organization_data["updated_at"] = datetime.now(timezone.utc)

        organization_data["status"] = "active"

        try:

            organization = await self.repository.create(
                organization_data
            )

            return organization

        except DuplicateKeyError:

            raise ValueError(
                "Organization with this slug already exists"
            )

    async def get_organization(self, organization_id: str):

        organization = await self.repository.get_by_id(
            organization_id
        )

        if organization is None:

            raise ValueError("Organization not found")

        return organization

    async def update_organization(self, organization_id: str, update_data: dict):
        if not update_data:
            raise ValueError("At least one field is required for update")

        organization = await self.repository.get_by_id(organization_id)

        if organization is None:
            raise ValueError("Organization not found")

        update_data["updated_at"] = datetime.now(timezone.utc)

        try:
            updated_organization = await self.repository.update(
                organization_id,
                update_data
            )

            return updated_organization

        except DuplicateKeyError:
            raise ValueError("An organization with this slug already exists")

    async def update_organization_status(self, organization_id: str, new_status: str):
        organization = await self.repository.get_by_id(organization_id)

        if organization is None:
            raise ValueError("Organization not found")

        return await self.repository.update(
            organization_id,
            {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc)
            }
        )
