import logging

from flask_smorest import abort

from app.db import db
from app.models.role_model import RoleModel
from app.models.user_model import UserModel
from app.utils.authorization import ensure_caller_keeps_admin, get_or_404

# Create logger for this module
logger = logging.getLogger(__name__)


def link_roles_to_user(user_id, role_id):
    user = get_or_404(UserModel, user_id, "User")
    role = get_or_404(RoleModel, role_id, "Role")

    if role in user.roles:
        abort(400, message="User already has this role.")

    user.roles.append(role)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("An error occurred while inserting the role.")
        abort(500, message="An error occurred while inserting the role.")

    return role


def delete_roles_to_user(user_id, role_id):
    user = get_or_404(UserModel, user_id, "User")
    role = get_or_404(RoleModel, role_id, "Role")

    if role not in user.roles:
        abort(400, message="User does not have this role.")

    user.roles.remove(role)
    ensure_caller_keeps_admin()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("An error occurred while deleting the role.")
        abort(500, message="An error occurred while deleting the role.")

    return {"message": "User removed from role", "user": user, "role": role}
