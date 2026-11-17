import asyncio
import getpass
import re
import sys
from pathlib import Path

# Add backend directory to Python import path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import mongodb
from app.services.platform_admin_service import (
    PlatformAdminService
)


def validate_email(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.fullmatch(pattern, email))


async def create_super_admin():

    try:
        print("\n=== Office System HRMS ===")
        print("Create First Super Admin\n")

        full_name = input("Enter full name: ").strip()
        email = input("Enter email: ").strip().lower()

        if not full_name:
            print("Error: Full name is required.")
            return

        if not validate_email(email):
            print("Error: Enter a valid email address.")
            return

        password = getpass.getpass("Enter password: ")
        confirm_password = getpass.getpass(
            "Confirm password: "
        )

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        # Connect to MongoDB
        await mongodb.connect()

        db = mongodb.get_database()

        service = PlatformAdminService(db)

        admin = await service.create_first_admin(
            full_name=full_name,
            email=email,
            password=password
        )

        print("\nSuper Admin created successfully!")
        print(f"Admin ID: {admin['id']}")
        print(f"Name: {admin['full_name']}")
        print(f"Email: {admin['email']}")
        print(f"Role: {admin['role']}")

    except ValueError as error:
        print(f"\nCreation failed: {error}")

    except Exception as error:
        print(f"\nUnexpected error: {error}")
        raise

    finally:
        await mongodb.close()


if __name__ == "__main__":
    asyncio.run(create_super_admin())
