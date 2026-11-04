from fastapi import APIRouter, Request, HTTPException
from pymongo.errors import PyMongoError

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():

    return {
        "status": "success",
        "message": "Office System HRMS is running"
    }


@router.get("/ready")
async def readiness_check(request: Request):

    try:

        await request.app.state.mongo_client.admin.command(
            "ping"
        )

        return {
            "status": "ready",
            "database": "connected"
        }

    except (PyMongoError, AttributeError):

        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": "unavailable"
            }
        )
