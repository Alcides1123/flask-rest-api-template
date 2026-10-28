import logging
import time
from functools import wraps

from flask_jwt_extended import current_user
from flask_smorest import abort

from app.utils.authorization import has_permission

# Create logger for this module
logger = logging.getLogger(__name__)


def permission_required(permission_name):
    """
    Reject the request with 403 unless the authenticated user holds the
    permission through one of their roles. Must be applied *after*
    jwt_required() (i.e. listed below it), since it relies on the verified JWT.
    """

    def decorator(func):
        # wraps() copies the function metadata (including the _apidoc attribute
        # that flask-smorest attaches), so Swagger docs survive this decorator.
        @wraps(func)
        def wrapper(*arg, **kwargs):
            if not has_permission(current_user, permission_name):
                logger.warning(
                    "User %s lacks permission '%s' for %s",
                    current_user.id,
                    permission_name,
                    func.__qualname__,
                )
                abort(403, message="User does not have permission to access this API!")
            return func(*arg, **kwargs)

        return wrapper

    return decorator


def time_profiling(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Function {func.__name__} took {end_time-start_time:.4f}s.")
        return result

    return wrapper
