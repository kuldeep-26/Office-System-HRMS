async def create_database_indexes(db):
    """
    Create indexes required by the Office System HRMS.
    """

    # 1. Organizations
    await db.organizations.create_index(
        [("slug", 1)],
        unique=True,
        name="unique_organization_slug"
    )

    # 2. Users
    await db.users.create_index(
        [
            ("organization_id", 1),
            ("email", 1)
        ],
        unique=True,
        name="unique_user_email_per_org"
    )

    await db.users.create_index(
        [
            ("organization_id", 1),
            ("status", 1)
        ],
        name="users_by_org_status"
    )

    # 3. Employees
    await db.employees.create_index(
        [
            ("organization_id", 1),
            ("employee_code", 1)
        ],
        unique=True,
        name="unique_employee_code_per_org"
    )

    await db.employees.create_index(
        [
            ("organization_id", 1),
            ("status", 1)
        ],
        name="employees_by_org_status"
    )

    # 4. Departments
    await db.departments.create_index(
        [
            ("organization_id", 1),
            ("normalized_name", 1)
        ],
        unique=True,
        name="unique_department_name_per_org"
    )

    # 5. Designations
    await db.designations.create_index(
        [
            ("organization_id", 1),
            ("normalized_name", 1)
        ],
        unique=True,
        name="unique_designation_name_per_org"
    )

    # 6. Branches
    await db.branches.create_index(
        [
            ("organization_id", 1),
            ("normalized_name", 1)
        ],
        unique=True,
        name="unique_branch_name_per_org"
    )

    # 7. Roles
    await db.roles.create_index(
        [
            ("scope", 1),
            ("name", 1)
        ],
        unique=True,
        name="unique_role_per_scope"
    )

    # 8. Permissions
    await db.permissions.create_index(
        [("permission_key", 1)],
        unique=True,
        name="unique_permission_key"
    )

    # 9. Attendance
    await db.attendance_records.create_index(
        [
            ("organization_id", 1),
            ("employee_id", 1),
            ("event_time", 1)
        ],
        name="attendance_by_org_employee_time"
    )

    await db.attendance_records.create_index(
        [
            ("organization_id", 1),
            ("idempotency_key", 1)
        ],
        unique=True,
        partialFilterExpression={
            "idempotency_key": {"$type": "string"}
        },
        name="unique_attendance_idempotency"
    )

    # 10. Face enrollments
    await db.face_enrollments.create_index(
        [
            ("organization_id", 1),
            ("employee_id", 1)
        ],
        unique=True,
        name="unique_face_enrollment_per_employee"
    )

    await db.face_enrollments.create_index(
        [
            ("organization_id", 1),
            ("status", 1)
        ],
        name="face_enrollment_by_org_status"
    )

    # 11. Leave requests
    await db.leave_requests.create_index(
        [
            ("organization_id", 1),
            ("employee_id", 1),
            ("start_date", 1),
            ("end_date", 1)
        ],
        name="leave_by_employee_period"
    )

    await db.leave_requests.create_index(
        [
            ("organization_id", 1),
            ("status", 1)
        ],
        name="leave_by_org_status"
    )

    # 12. Payroll
    await db.payroll_runs.create_index(
        [
            ("organization_id", 1),
            ("period", 1),
            ("status", 1)
        ],
        name="payroll_by_org_period_status"
    )

    # 13. Documents
    await db.documents.create_index(
        [
            ("organization_id", 1),
            ("owner_id", 1),
            ("category", 1)
        ],
        name="documents_by_owner_category"
    )

    # 14. Tasks
    await db.tasks.create_index(
        [
            ("organization_id", 1),
            ("assignee_id", 1),
            ("due_date", 1)
        ],
        name="tasks_by_assignee_due_date"
    )

    # 15. Projects
    await db.projects.create_index(
        [
            ("organization_id", 1),
            ("status", 1)
        ],
        name="projects_by_org_status"
    )

    # 16. Notifications
    await db.notifications.create_index(
        [
            ("organization_id", 1),
            ("recipient_id", 1),
            ("created_at", -1)
        ],
        name="notifications_by_recipient"
    )

    # 17. Refresh token sessions
    await db.refresh_token_sessions.create_index(
        [("token_hash", 1)],
        unique=True,
        name="unique_refresh_token_hash"
    )

    await db.refresh_token_sessions.create_index(
        [
            ("user_id", 1),
            ("expires_at", 1)
        ],
        name="refresh_sessions_by_user_expiry"
    )

    # 18. Audit logs
    await db.audit_logs.create_index(
        [
            ("organization_id", 1),
            ("timestamp", -1)
        ],
        name="audit_by_org_timestamp"
    )

    print("All MongoDB indexes created successfully.")
