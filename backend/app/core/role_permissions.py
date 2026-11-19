
ROLE_PERMISSION_MAPPING = {

    "org_admin": [
        # All organization-level permissions
        "employee:create",
        "employee:read",
        "employee:update",
        "employee:delete",

        "department:create",
        "department:read",
        "department:update",
        "department:delete",

        "designation:create",
        "designation:read",
        "designation:update",
        "designation:delete",

        "branch:create",
        "branch:read",
        "branch:update",
        "branch:delete",

        "attendance:read",
        "attendance:manage",

        "leave:create",
        "leave:read",
        "leave:approve",

        "payroll:read",
        "payroll:manage",

        "document:upload",
        "document:read",
        "document:delete",

        "task:create",
        "task:read",
        "task:update",
        "task:delete",

        "project:create",
        "project:read",
        "project:update",
        "project:delete",
    ],

    "hr_manager": [
        "employee:create",
        "employee:read",
        "employee:update",

        "department:read",
        "designation:read",
        "branch:read",

        "attendance:read",
        "attendance:manage",

        "leave:create",
        "leave:read",
        "leave:approve",

        "document:upload",
        "document:read",
    ],

    "manager": [
        "employee:read",
        "department:read",
        "designation:read",
        "branch:read",

        "attendance:read",
        "leave:read",
        "leave:approve",

        "task:create",
        "task:read",
        "task:update",

        "project:create",
        "project:read",
        "project:update",
    ],

    "employee": [
        "employee:read",
        "attendance:read",
        "leave:create",
        "leave:read",
        "document:upload",
        "document:read",
        "task:read",
        "project:read",
    ]
}
