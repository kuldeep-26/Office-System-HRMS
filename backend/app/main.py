from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.db.connection import mongodb
from app.db.init_db import initialize_database

from app.api.routes.health import router as health_router
from app.api.routes.organizations import router as organization_router
from app.api.routes.auth import router as auth_router
from app.api.routes.platform_auth import router as platform_auth_router
from app.api.routes.rbac_test import router as rbac_test_router
from app.api.routes.employees import router as employees_router
from app.api.routes.departments import router as departments_router
from app.api.routes.designations import router as designations_router
from app.api.routes.branches import router as branches_router
from app.api.routes.documents import router as documents_router
from app.api.routes.employee_accounts import router as employee_accounts_router
from app.api.routes.face_enrollments import router as face_enrollments_router
from app.api.routes.attendance import router as attendance_router

@asynccontextmanager
async def lifespan(app: FastAPI):

    # 1. Connect MongoDB
    await mongodb.connect()

    # 2. Get database
    db = mongodb.get_database()

    # 3. Initialize database indexes
    await initialize_database(db)

    # 4. Store database references
    app.state.mongo_client = mongodb.client
    app.state.database = db

    print("Application startup completed")

    yield

    # Shutdown
    await mongodb.close()

    print("Application shutdown completed")



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-organization Human Resource Management System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


app.include_router(health_router)


@app.get("/")
async def root():

    return {
        "message": "Welcome to Office System HRMS",
        "version": settings.APP_VERSION
    }

app.include_router(
    organization_router,
    prefix=settings.API_V1_PREFIX
)

app.include_router(
    auth_router,
    prefix=settings.API_V1_PREFIX
)

app.include_router(
    platform_auth_router,
    prefix=settings.API_V1_PREFIX
)

app.include_router(
    rbac_test_router,
    prefix=settings.API_V1_PREFIX
)

app.include_router(
    employees_router,
    prefix="/api/v1"
)

app.include_router(
    employee_accounts_router,
    prefix="/api/v1"
)

app.include_router(
    departments_router,
    prefix="/api/v1"
)

app.include_router(
    designations_router,
    prefix="/api/v1"
)

app.include_router(
    branches_router,
    prefix="/api/v1"
)

app.include_router(
    documents_router,
    prefix="/api/v1"
)

app.include_router(
    face_enrollments_router,
    prefix="/api/v1"
)

app.include_router(
    attendance_router,
    prefix="/api/v1"
)