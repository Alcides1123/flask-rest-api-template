import logging
from datetime import datetime, timezone

from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
)
from flask_smorest import abort
from passlib.hash import pbkdf2_sha256
from sqlalchemy import asc
from werkzeug.exceptions import HTTPException

from app.db import db
from app.models.blocklist_model import BlocklistModel
from app.models.role_model import RoleModel
from app.models.user_model import UserModel
from app.utils.authorization import (
    current_user_id,
    current_user_is_admin,
    ensure_caller_keeps_admin,
    get_or_404,
)

# Role given to every newly registered user
DEFAULT_ROLE_NAME = "Guest"

# Create logger for this module
logger = logging.getLogger(__name__)


def get_all_user():
    results = UserModel.query.order_by(asc(UserModel.id)).all()
    return results


def get_user(user_id):
    return get_or_404(UserModel, user_id, "User")


def update_user(user_data, user_id):
    """
    Update a user. Users may change their own username / password; only an
    admin may update other users or change role assignments.
    """
    is_admin = current_user_is_admin()

    if not is_admin and user_id != current_user_id():
        logger.warning("User %s tried to update user %s", current_user_id(), user_id)
        abort(403, message="You can only update your own account.")

    if user_data.get("roles") is not None and not is_admin:
        logger.warning("User %s tried to change roles", current_user_id())
        abort(403, message="Only an admin can change roles.")

    user = get_or_404(UserModel, user_id, "User")

    try:
        if user_data.get("username"):
            user.username = user_data["username"]

        if user_data.get("password"):
            # Hash password
            user.password = pbkdf2_sha256.hash(user_data["password"])

        if user_data.get("roles") is not None:
            user.roles = [
                get_or_404(RoleModel, role_id, "Role") for role_id in user_data["roles"]
            ]
            ensure_caller_keeps_admin()

        db.session.commit()
    except HTTPException:
        raise
    except Exception:
        db.session.rollback()
        logger.exception("Can not update!")
        abort(400, message="Can not update!")

    return {"message": "Update successfully!"}


def update_block_user(user_data, user_id):
    """
    Block / unblock a user. Requires the admin permission (enforced by the
    router); an admin cannot block their own account.
    """
    if user_id == current_user_id():
        abort(400, message="You can not block your own account.")

    user = get_or_404(UserModel, user_id, "User")

    try:
        # Update status block
        user.block = user_data["block"]

        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not update status block User!")
        abort(400, message="Can not update status block User!")

    return {"message": "Block successfully!"}


def login_user(user_data):
    # Check user name
    user = UserModel.query.filter(UserModel.username == user_data["username"]).first()

    # Verify
    if user and pbkdf2_sha256.verify(user_data["password"], user.password):
        logger.info(f"User login successfully! user_name: {user_data['username']}")
        return create_token_pair(user.id, fresh=True)

    logger.error("Invalid credentials.")
    abort(401, message="Invalid credentials.")


def register_user(user_data):
    username = user_data["username"]
    password = user_data["password"]

    # Check user name exist
    user = UserModel.query.filter(UserModel.username == user_data["username"]).first()
    if user:
        logger.error("Username already exists.")
        abort(400, message="Username already exists.")

    default_role = RoleModel.query.filter_by(name=DEFAULT_ROLE_NAME).first()
    if default_role is None:
        logger.error(
            "Default role '%s' is missing - run `flask create-user-admin`",
            DEFAULT_ROLE_NAME,
        )
        abort(500, message="Registration is not available.")

    # Hash password
    password = pbkdf2_sha256.hash(password)

    new_user = UserModel(username=username, password=password)
    new_user.roles.append(default_role)

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Can not register!")
        abort(400, message="Can not register!")

    return {"message": "Register successfully!"}


def create_token_pair(user_id, fresh=False):
    """
    Create an access/refresh token pair.

    The refresh token is created first so that its jti can be embedded in the
    access token (claim "refresh_jti"). That lets /logout revoke both tokens
    of the pair even though the client only presents the access token.
    """
    # "sub" must be a string (RFC 7519); see authorization.current_user_id()
    identity = str(user_id)

    refresh_token = create_refresh_token(identity=identity)
    refresh_jti = decode_token(refresh_token)["jti"]

    access_token = create_access_token(
        identity=identity,
        fresh=fresh,
        additional_claims={"refresh_jti": refresh_jti},
    )

    return {"access_token": access_token, "refresh_token": refresh_token}


def logout_user():
    """
    Revoke the current access token and the refresh token that was issued
    together with it.
    """
    jwt = get_jwt()
    add_jti_blocklist(jwt["jti"], expires_at=_from_timestamp(jwt["exp"]))

    refresh_jti = jwt.get("refresh_jti")
    if refresh_jti:
        # The refresh token's own exp is not at hand; its lifetime is an upper bound
        add_jti_blocklist(
            refresh_jti,
            expires_at=datetime.now(timezone.utc)
            + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
        )

    return {"message": "Logout successfully!"}


def refresh_token():
    # Get id current user
    user_id = current_user_id()

    # Refresh tokens are single-use: revoke the one that was just presented.
    # NOTE: the access token that was paired with it is *not* revoked here
    # (its jti is not known in this context) and stays valid until it expires.
    jwt = get_jwt()
    add_jti_blocklist(jwt["jti"], expires_at=_from_timestamp(jwt["exp"]))

    return create_token_pair(user_id, fresh=False)


def _from_timestamp(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp, timezone.utc)


def add_jti_blocklist(jti, expires_at=None):
    """
    Add a token id to the blocklist. Idempotent: revoking an already revoked
    token is not an error. expires_at lets prune_blocklist() drop the row once
    the token could no longer be used anyway.
    """
    if db.session.get(BlocklistModel, str(jti)) is not None:
        return

    try:
        db.session.add(BlocklistModel(jti_blocklist=str(jti), expires_at=expires_at))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Could not add token %s to the blocklist", jti)
        abort(500, message="Could not revoke token.")
