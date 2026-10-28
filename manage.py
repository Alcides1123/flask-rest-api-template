import sys
import unittest
from datetime import datetime, timezone

import click
from passlib.hash import pbkdf2_sha256

from app.db import db
from app.models import BlocklistModel, PermissionModel, RoleModel, UserModel
from app.utils.authorization import ADMIN_PERMISSION


@click.option(
    "--pattern", default="tests_*.py", help="Test search pattern", required=False
)
def cov(pattern):
    """
    Run the unit tests with coverage
    """
    import coverage  # dev dependency (requirements-dev.txt), not needed at runtime

    cov = coverage.coverage(branch=True, include="app/*")
    cov.start()
    tests = unittest.TestLoader().discover("tests", pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        cov.stop()
        cov.save()
        print("Coverage Summary:")
        cov.report()
        cov.erase()
        sys.exit(0)
    # A non-zero exit code is what makes CI fail; Click ignores return values.
    sys.exit(1)


@click.option(
    "--pattern", default="tests_*.py", help="Test search pattern", required=False
)
def cov_html(pattern):
    """
    Run the unit tests with coverage and generate an HTML report.
    """
    import coverage  # dev dependency (requirements-dev.txt), not needed at runtime

    cov = coverage.coverage(branch=True, include="app/*")
    cov.start()

    tests = unittest.TestLoader().discover("tests", pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(tests)

    if result.wasSuccessful():
        cov.stop()
        cov.save()

        print("Coverage Summary:")
        cov.report()
        cov.html_report(directory="report/htmlcov")
        cov.erase()
        sys.exit(0)

    sys.exit(1)


@click.option("--pattern", default="tests_*.py", help="Test pattern", required=False)
def tests(pattern):
    """
    Run the tests without code coverage
    """
    tests = unittest.TestLoader().discover("tests", pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    sys.exit(0 if result.wasSuccessful() else 1)


def create_db():
    """
    Create Database.
    """
    db.create_all()
    db.session.commit()


def reset_db():
    """
    Reset Database.
    """
    db.drop_all()
    db.create_all()
    db.session.commit()


def drop_db():
    """
    Drop Database.
    """
    db.drop_all()
    db.session.commit()


# Seed data. Passwords are for local development only - see README "Default Seed Accounts".
SEED_PASSWORD = "123456"

SEED_PERMISSIONS = {
    "read": "Read data",
    "write": "Write data",
    "delete": "Delete data",
    ADMIN_PERMISSION: "Manage users, roles and permissions",
}

# role name -> (description, permissions)
SEED_ROLES = {
    "Admin": ("Full Permission", ["read", "write", "delete", ADMIN_PERMISSION]),
    "User": ("Can read, write data", ["read", "write"]),
    "Guest": ("Just read data", ["read"]),
}

# username -> role
SEED_USERS = {"admin": "Admin", "user": "User", "guest": "Guest"}


def init_db_user():
    """
    Seed permissions, roles and users. Relationships are built from objects,
    not hard-coded ids, so the result does not depend on sequence values.
    """
    permissions = {
        name: PermissionModel(name=name, description=description)
        for name, description in SEED_PERMISSIONS.items()
    }
    db.session.add_all(permissions.values())

    roles = {}
    for name, (description, permission_names) in SEED_ROLES.items():
        role = RoleModel(name=name, description=description)
        role.permissions = [permissions[p] for p in permission_names]
        roles[name] = role
    db.session.add_all(roles.values())

    password = pbkdf2_sha256.hash(SEED_PASSWORD)
    for username, role_name in SEED_USERS.items():
        user = UserModel(username=username, password=password)
        user.roles.append(roles[role_name])
        db.session.add(user)

    db.session.commit()


def ensure_admin_permission():
    """
    Upgrade path for databases seeded before the "admin" permission existed:
    create it if missing and grant it to the "Admin" role.
    """
    permission = PermissionModel.query.filter_by(name=ADMIN_PERMISSION).first()
    if permission is None:
        permission = PermissionModel(
            name=ADMIN_PERMISSION, description=SEED_PERMISSIONS[ADMIN_PERMISSION]
        )
        db.session.add(permission)
        print(f"Created missing '{ADMIN_PERMISSION}' permission.")

    admin_role = RoleModel.query.filter_by(name="Admin").first()
    if admin_role is not None and permission not in admin_role.permissions:
        admin_role.permissions.append(permission)
        print(f"Granted '{ADMIN_PERMISSION}' permission to the Admin role.")

    db.session.commit()


def create_user_admin(username="admin"):
    """
    Create User Admin.
    """
    admin = UserModel.query.filter_by(username=username).first()

    if admin is None:
        print("user-admin is not created before!")
        init_db_user()
    else:
        print("user-admin is created!")
        ensure_admin_permission()


def prune_blocklist():
    """
    Delete revoked-token rows whose token has expired anyway. Run periodically
    (cron / scheduler) to keep the blocklist table small.
    """
    now = datetime.now(timezone.utc)
    # synchronize_session=False: no loaded objects need updating, and it avoids
    # Python-side comparison of naive (SQLite) vs aware datetimes.
    deleted = BlocklistModel.query.filter(BlocklistModel.expires_at < now).delete(
        synchronize_session=False
    )
    db.session.commit()
    print(f"Pruned {deleted} expired blocklist entries.")
    return deleted


def init_app(app):
    if app.config["APP_ENV"] == "production":
        commands = [create_db, reset_db, drop_db, create_user_admin, prune_blocklist]
    else:
        commands = [
            create_db,
            reset_db,
            drop_db,
            create_user_admin,
            prune_blocklist,
            tests,
            cov_html,
            cov,
        ]

    for command in commands:
        app.cli.add_command(app.cli.command()(command))
