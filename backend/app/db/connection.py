from pymongo import AsyncMongoClient
from app.core.config import settings

class MongoDB:

    def __init__(self):
        self.client = None
        self.database = None

    async def connect(self):

        try:
            self.client = AsyncMongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000
            )

            # Verify MongoDB connection
            await self.client.admin.command("ping")

            # Select database
            self.database = self.client[
                settings.MONGODB_DATABASE
            ]

            print("MongoDB connected successfully")

        except Exception:
            if self.client is not None:
                await self.client.close()

            self.client = None
            self.database = None

            raise

    async def close(self):

        if self.client is not None:

            await self.client.close()

            self.client = None
            self.database = None

            print("MongoDB connection closed")

    def get_database(self):

        if self.database is None:
            raise RuntimeError(
                "MongoDB database is not initialized"
            )

        return self.database


# Global database manager instance
mongodb = MongoDB()
