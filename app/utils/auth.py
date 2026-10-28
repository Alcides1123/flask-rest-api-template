from flask import jsonify
from sqlalchemy.orm import selectinload

from app.db import db
from app.extensions import jwt
from app.models import BlocklistModel, RoleModel, UserModel


@jwt.user_lookup_loader
def load_user_from_token(jwt_header, jwt_data):
    """
    Load the token's user once per request (available as
    flask_jwt_extended.current_user), together with roles and permissions so
    that authorization checks need no further queries.

    Returning None makes Flask-JWT-Extended reject the request through
    user_lookup_error_callback - used for blocked or deleted users, so that
    blocking takes effect on the user's next request.
    """
    user = db.session.get(
        UserModel,
        int(jwt_data["sub"]),
        options=[selectinload(UserModel.roles).selectinload(RoleModel.permissions)],
    )
    if user is None or user.block:
        return None
    return user


@jwt.user_lookup_error_loader
def user_lookup_error_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {
                "description": "The user is blocked or no longer exists",
                "error": "user_blocked",
            }
        ),
        401,
    )


@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    return db.session.get(BlocklistModel, jwt_payload["jti"]) is not None


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {"description": "The token has been revoked", "error": "token_revoked"}
        ),
        401,
    )


@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {"description": "The token is not fresh", "error": "fresh_token_reqired"}
        ),
        401,
    )


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"message": "Token has expired.", "error": "token_expired"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return (
        jsonify(
            {"message": "Signature verification failed.", "error": "invalid_token"}
        ),
        401,
    )


@jwt.unauthorized_loader
def miss_token_callback(error):
    return (
        jsonify(
            {
                "description": "Request does not contain an access token",
                "error": "authorization_required",
            }
        ),
        401,
    )
