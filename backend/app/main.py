from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.db.connection import mongodb
from app.db.init_db import initialize_database
from app.api.routes.health import router as health_router



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