from app.db.indexes import create_database_indexes


async def initialize_database(db):

    print("Initializing Office System HRMS database...")

    await create_database_indexes(db)

    print("Database initialization completed.")
