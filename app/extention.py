from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

migrate = Migrate()
jwt = JWTManager()
cors = CORS()
# Limits are keyed by client IP; see TRUSTED_PROXY_COUNT in config.py when
# running behind a reverse proxy.
limiter = Limiter(key_func=get_remote_address)
