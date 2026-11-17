from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError
from app.db.dependencies import get_database
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationStatusUpdate
)
from app.services.organization_service import (
    OrganizationService
)
from app.api.dependencies.platform_auth import (
    get_current_platform_admin
)


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
    dependencies=[
        Depends(get_current_platform_admin)
    ]
)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_organization(
    organization_data: OrganizationCreate,
    db=Depends(get_database)
):

    service = OrganizationService(db)

    try:

        organization = await service.create_organization(
            organization_data.model_dump()
        )

        return {
            "id": str(organization["_id"]),
            "name": organization["name"],
            "slug": organization["slug"],
            "timezone": organization["timezone"],
            "currency": organization["currency"],
            "status": organization["status"]
        }

    except ValueError as error:

        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except PyMongoError:

        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse
)
async def get_organization(
    organization_id: str,
    db=Depends(get_database)
):

    service = OrganizationService(db)

    try:

        organization = await service.get_organization(
            organization_id
        )

        return {
            "id": str(organization["_id"]),
            "name": organization["name"],
            "slug": organization["slug"],
            "timezone": organization["timezone"],
            "currency": organization["currency"],
            "status": organization["status"]
        }

    except ValueError:

        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    except PyMongoError:

        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )

@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    organization_data: OrganizationUpdate,
    db=Depends(get_database)
):
    service = OrganizationService(db)

    update_data = organization_data.model_dump(exclude_unset=True)

    try:
        organization = await service.update_organization(
            organization_id,
            update_data
        )

        return {
            "id": str(organization["_id"]),
            "name": organization["name"],
            "slug": organization["slug"],
            "timezone": organization["timezone"],
            "currency": organization["currency"],
            "status": organization["status"]
        }

    except ValueError as error:
        message = str(error)

        error_status = (
            409 if "already exists" in message
            else 404 if "not found" in message
            else 400
        )

        raise HTTPException(status_code=error_status, detail=message)

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )


@router.patch("/{organization_id}/status", response_model=OrganizationResponse)
async def update_organization_status(
    organization_id: str,
    status_data: OrganizationStatusUpdate,
    db=Depends(get_database)
):
    service = OrganizationService(db)

    try:
        organization = await service.update_organization_status(
            organization_id,
            status_data.status
        )

        return {
            "id": str(organization["_id"]),
            "name": organization["name"],
            "slug": organization["slug"],
            "timezone": organization["timezone"],
            "currency": organization["currency"],
            "status": organization["status"]
        }

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    except PyMongoError:
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )