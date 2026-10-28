import logging

from flask_smorest import abort

from app.db import db
from app.models.permission_model import PermissionModel
from app.models.role_model import RoleModel
from app.models.role_permission_model import RolePermissionModel
from app.utils.authorization import ensure_caller_keeps_admin, get_or_404

# Create logger for this module
logger = logging.getLogger(__name__)


def get_role_permission():
    results = RolePermissionModel.query.all()
    return results


def update_roles_to_permission(permission_data):
    """
    Replace the roles of each permission in {permission_id: [role_id, ...]}.
    All changes are applied in a single transaction.
    """
    for permission_id, role_ids in permission_data["data_update"].items():
        try:
            permission_id = int(permission_id)
        except (TypeError, ValueError):
            abort(400, message=f"Invalid permission id: {permission_id!r}")

        permission = get_or_404(PermissionModel, permission_id, "Permission")
        permission.roles = [get_or_404(RoleModel, rid, "Role") for rid in role_ids]

    ensure_caller_keeps_admin()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("An error occurred while inserting the roles.")
        abort(500, message="An error occurred while inserting the roles.")

    return {"message": "Update successfully!"}
