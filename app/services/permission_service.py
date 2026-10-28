import logging

from flask_smorest import abort
from sqlalchemy import asc

from app.db import db
from app.models.permission_model import PermissionModel
from app.utils.authorization import ensure_caller_keeps_admin, get_or_404

# Create logger for this module
logger = logging.getLogger(__name__)


def get_all_permission():
    results = PermissionModel.query.order_by(asc(PermissionModel.id)).all()
    return results


def post_permission(permission_data):
    name = permission_data["name"]
    description = permission_data["description"]

    try:
        new_row = PermissionModel(name=name, description=description)

        db.session.add(new_row)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not add permission!")
        abort(400, message="Can not add permission!")

    return {"message": "Add successfully!"}


def get_permission(permission_id):
    results = PermissionModel.query.filter_by(id=permission_id).first()
    return results


def update_permission(permission_data, permission_id):
    permission = get_or_404(PermissionModel, permission_id, "Permission")

    if permission_data["name"]:
        permission.name = permission_data["name"]

    if permission_data["description"]:
        permission.description = permission_data["description"]

    # Renaming the admin permission would lock every admin out
    ensure_caller_keeps_admin()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not update permission!")
        abort(400, message="Can not update permission!")

    return {"message": "Update successfully!"}
