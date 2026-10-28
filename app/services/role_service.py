import logging

from flask_smorest import abort
from sqlalchemy import asc

from app.db import db
from app.models.permission_model import PermissionModel
from app.models.role_model import RoleModel
from app.utils.authorization import ensure_caller_keeps_admin, get_or_404

# Create logger for this module
logger = logging.getLogger(__name__)


def _permissions_from_ids(permission_ids):
    return [get_or_404(PermissionModel, pid, "Permission") for pid in permission_ids]


def get_all_role():
    results = RoleModel.query.order_by(asc(RoleModel.id)).all()
    return results


def post_role(role_data):
    permissions = _permissions_from_ids(role_data["permissions"])

    new_row = RoleModel(name=role_data["name"], description=role_data["description"])
    new_row.permissions = permissions

    try:
        db.session.add(new_row)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not add role!")
        abort(400, message="Can not add role!")

    return {"message": "Add successfully!"}


def get_role(role_id):
    return get_or_404(RoleModel, role_id, "Role")


def update_role(role_data, role_id):
    role = get_or_404(RoleModel, role_id, "Role")
    permissions = _permissions_from_ids(role_data["permissions"])

    role.permissions = permissions

    if role_data["name"]:
        role.name = role_data["name"]

    if role_data["description"]:
        role.description = role_data["description"]

    # Changing a role's permissions changes what every user holding it may do
    ensure_caller_keeps_admin()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not update role!")
        abort(400, message="Can not update role!")

    return {"message": "Update successfully!"}


def delete_role(role_id):
    role = get_or_404(RoleModel, role_id, "Role")

    # ORM delete so the role_permission / user_role link rows are removed too
    db.session.delete(role)
    ensure_caller_keeps_admin()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not delete role!")
        abort(400, message="Can not delete role!")

    return {"message": "Delete successfully!"}
