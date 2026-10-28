"""
Authorization helpers.

The permission model is role based: a user has roles, a role has permissions.
Data access is gated by the "read" / "write" / "delete" permissions; anything
that changes *who is allowed to do what* (roles, permissions, role assignments,
blocking users) additionally requires the ADMIN_PERMISSION.

All checks query the database, so a change of roles takes effect on the very
next request - nothing authorization related is cached inside the JWT.
"""
import logging

from flask_jwt_extended import get_jwt_identity
from flask_smorest import abort

from app.db import db
from app.models.permission_model import PermissionModel
from app.models.role_model import RoleModel
from app.models.user_model import UserModel

ADMIN_PERMISSION = "admin"

logger = logging.getLogger(__name__)


def user_has_permission(user_id, permission_name):
    """
    Return True if the user holds the permission through any of their roles.
    Single query, no N+1 over roles / permissions.
    """
    return (
        db.session.query(UserModel.id)
        .join(UserModel.roles)
        .join(RoleModel.permissions)
        .filter(UserModel.id == user_id, PermissionModel.name == permission_name)
        .first()
        is not None
    )


def current_user_id():
    return get_jwt_identity()


def current_user_is_admin():
    return user_has_permission(current_user_id(), ADMIN_PERMISSION)


def ensure_caller_keeps_admin():
    """
    Guard against locking yourself out.

    Call this *before* committing any change to roles / permissions / role
    assignments. It flushes the pending changes and verifies the caller still
    holds the admin permission; if not, the transaction is rolled back and the
    request is rejected.
    """
    db.session.flush()
    if not user_has_permission(current_user_id(), ADMIN_PERMISSION):
        db.session.rollback()
        logger.warning(
            "User %s attempted a change that would remove their own admin access",
            current_user_id(),
        )
        abort(400, message="This change would remove your own admin access.")


def get_or_404(model, object_id, label):
    """
    Fetch a row by primary key or abort with a JSON 404.
    """
    obj = db.session.get(model, object_id)
    if obj is None:
        abort(404, message=f"{label} {object_id} does not exist.")
    return obj
