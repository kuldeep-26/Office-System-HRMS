from datetime import datetime, timezone

from app.db.indexes import create_database_indexes
from app.core.role_permissions import ROLE_PERMISSION_MAPPING


async def seed_system_roles(db):
    """
    Create required system roles if they do not exist.
    """

    now = datetime.now(timezone.utc)

    await db.roles.update_one(
        {
            "scope": "organization",
            "name": "org_admin"
        },
        {
            "$setOnInsert": {
                "scope": "organization",
                "name": "org_admin",
                "description": "Organization Administrator",
                "permission_keys": [],
                "is_system": True,
                "created_at": now,
                "updated_at": now
            }
        },
        upsert=True
    )

    print("System roles initialized successfully.")


async def seed_system_permissions(db):
    """
    Create the centralized HRMS permission catalog.
    """

    now = datetime.now(timezone.utc)

    permissions = [
        # Employees
        ("employee:create", "employees", "Create employees"),
        ("employee:read", "employees", "View employees"),
        ("employee:update", "employees", "Update employees"),
        ("employee:delete", "employees", "Delete employees"),

        # Departments
        ("department:create", "departments", "Create departments"),
        ("department:read", "departments", "View departments"),
        ("department:update", "departments", "Update departments"),
        ("department:delete", "departments", "Delete departments"),

        # Designations
        ("designation:create", "designations", "Create designations"),
        ("designation:read", "designations", "View designations"),
        ("designation:update", "designations", "Update designations"),
        ("designation:delete", "designations", "Delete designations"),

        # Branches
        ("branch:create", "branches", "Create branches"),
        ("branch:read", "branches", "View branches"),
        ("branch:update", "branches", "Update branches"),
        ("branch:delete", "branches", "Delete branches"),

        # Attendance
        ("attendance:read", "attendance", "View attendance"),
        ("attendance:manage", "attendance", "Manage attendance"),

        # Leave
        ("leave:create", "leave", "Create leave requests"),
        ("leave:read", "leave", "View leave requests"),
        ("leave:approve", "leave", "Approve leave requests"),

        # Payroll
        ("payroll:read", "payroll", "View payroll"),
        ("payroll:manage", "payroll", "Manage payroll"),

        # Documents
        ("document:upload", "documents", "Upload documents"),
        ("document:read", "documents", "View documents"),
        ("document:delete", "documents", "Delete documents"),

        # Tasks
        ("task:create", "tasks", "Create tasks"),
        ("task:read", "tasks", "View tasks"),
        ("task:update", "tasks", "Update tasks"),
        ("task:delete", "tasks", "Delete tasks"),

        # Projects
        ("project:create", "projects", "Create projects"),
        ("project:read", "projects", "View projects"),
        ("project:update", "projects", "Update projects"),
        ("project:delete", "projects", "Delete projects"),
    ]

    for permission_key, module, description in permissions:

        await db.permissions.update_one(
            {"permission_key": permission_key},
            {
                "$setOnInsert": {
                    "permission_key": permission_key,
                    "module": module,
                    "description": description,
                    "is_system": True,
                    "created_at": now,
                    "updated_at": now
                }
            },
            upsert=True
        )

    print("System permissions initialized successfully.")



async def seed_role_permissions(db):
    """
    Assign predefined permissions to system roles.
    """

    now = datetime.now(timezone.utc)

    for role_name, permission_keys in ROLE_PERMISSION_MAPPING.items():

        role = await db.roles.find_one({
            "scope": "organization",
            "name": role_name
        })

        if not role:
            await db.roles.insert_one({
                "scope": "organization",
                "name": role_name,
                "description": role_name.replace("_", " ").title(),
                "permission_keys": permission_keys,
                "is_system": True,
                "created_at": now,
                "updated_at": now
            })

        else:
            await db.roles.update_one(
                {"_id": role["_id"]},
                {
                    "$set": {
                        "permission_keys": permission_keys,
                        "updated_at": now
                    }
                }
            )

    print("Role permissions initialized successfully.")




async def initialize_database(db):

    print("Initializing Office System HRMS database...")

    await create_database_indexes(db)

    await seed_system_permissions(db)

    await seed_system_roles(db)

    await seed_role_permissions(db)

    print("Database initialization completed.")
