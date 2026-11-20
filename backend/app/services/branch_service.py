
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.repositories.branch_repository import BranchRepository


class BranchService:

    def __init__(self, db):
        self.db = db
        self.repository = BranchRepository(db)

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
        branch_name,
        exclude_id=None
    ):

        query = {
            "organization_id": ObjectId(organization_id),
            "normalized_name": branch_name.strip().casefold()
        }

        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}

        existing = await self.db.branches.find_one(query)

        if existing:
            raise ValueError("Branch name already exists")

    @staticmethod
    def _serialize(branch):

        if not branch:
            return None

        branch["id"] = str(branch.pop("_id"))
        branch["organization_id"] = str(
            branch["organization_id"]
        )

        return branch

    async def create_branch(self, organization_id, branch_data):

        await self._validate_organization(organization_id)

        await self._check_duplicate_name(
            organization_id,
            branch_data["branch_name"]
        )

        try:
            branch = await self.repository.create(
                organization_id,
                branch_data
            )

            return self._serialize(branch)

        except DuplicateKeyError:
            raise ValueError("Branch name already exists")

    async def get_branch(self, organization_id, branch_id):

        await self._validate_organization(organization_id)

        branch = await self.repository.get_by_id(
            organization_id,
            branch_id
        )

        return self._serialize(branch)

    async def get_all_branches(
        self,
        organization_id,
        skip=0,
        limit=20
    ):

        await self._validate_organization(organization_id)

        branches = await self.repository.get_all(
            organization_id,
            skip,
            limit
        )

        return [
            self._serialize(branch)
            for branch in branches
        ]

    async def update_branch(
        self,
        organization_id,
        branch_id,
        update_data
    ):

        await self._validate_organization(organization_id)

        existing = await self.repository.get_by_id(
            organization_id,
            branch_id
        )

        if not existing:
            return None

        if "branch_name" in update_data:
            await self._check_duplicate_name(
                organization_id,
                update_data["branch_name"],
                exclude_id=branch_id
            )

        try:
            branch = await self.repository.update(
                organization_id,
                branch_id,
                update_data
            )

            return self._serialize(branch)

        except DuplicateKeyError:
            raise ValueError("Branch name already exists")

    async def update_branch_status(
        self,
        organization_id,
        branch_id,
        new_status
    ):

        await self._validate_organization(organization_id)

        branch = await self.repository.update_status(
            organization_id,
            branch_id,
            new_status
        )

        return self._serialize(branch)
