from flask import current_app
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.extention import limiter
from app.schemas.user_schema import UpdateBlockUserSchema, UserSchema, UserUpdateSchema
from app.services import user_service
from app.utils.authorization import ADMIN_PERMISSION
from app.utils.decorators import permission_required

blp = Blueprint("User", __name__, description="User API")


@blp.route("/user")
class UserList(MethodView):
    @jwt_required()
    @permission_required(permission_name="read")
    @blp.response(200, UserSchema(many=True))
    def get(self):
        result = user_service.get_all_user()
        return result


@blp.route("/user/<int:user_id>")
class User(MethodView):
    @jwt_required()
    @permission_required(permission_name="read")
    @blp.response(200, UserSchema)
    def get(self, user_id):
        result = user_service.get_user(user_id)
        return result

    @jwt_required()
    @blp.arguments(UserUpdateSchema)
    def put(self, user_data, user_id):
        # Authorization is in the service: self-update, or admin for any user
        result = user_service.update_user(user_data, user_id)
        return result


@blp.route("/block-user/<int:user_id>")
class BlockUser(MethodView):
    @jwt_required()
    @permission_required(permission_name=ADMIN_PERMISSION)
    @blp.arguments(UpdateBlockUserSchema)
    def put(self, user_data, user_id):
        result = user_service.update_block_user(user_data, user_id)
        return result


@blp.route("/login")
class Login(MethodView):
    # Brute-force protection; limit string comes from config (RATELIMIT_LOGIN)
    decorators = [limiter.limit(lambda: current_app.config["RATELIMIT_LOGIN"])]

    @blp.arguments(UserSchema)
    def post(self, user_data):
        result = user_service.login_user(user_data)
        return result


@blp.route("/register")
class Register(MethodView):
    decorators = [limiter.limit(lambda: current_app.config["RATELIMIT_REGISTER"])]

    @blp.arguments(UserSchema)
    def post(self, user_data):
        result = user_service.register_user(user_data)
        return result


@blp.route("/logout")
class Logout(MethodView):
    @jwt_required()
    def post(self):
        # Revokes the access token and its paired refresh token
        result = user_service.logout_user()
        return result


@blp.route("/refresh")
class Refresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        result = user_service.refresh_token()

        return result
