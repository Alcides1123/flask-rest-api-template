import logging

from flask import Flask, jsonify
from werkzeug.exceptions import InternalServerError
from werkzeug.middleware.proxy_fix import ProxyFix

import manage
from app.blueprint import register_routing
from app.db import db
from app.extensions import cors, limiter, migrate
from app.utils.auth import jwt
from app.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings_module):
    """
    Application factory.

    settings_module: a config class or its import path, e.g.
    "config.DevelopConfig". Normally taken from APP_SETTINGS_MODULE (see
    wsgi.py); tests pass their own.
    """
    if not settings_module:
        raise RuntimeError(
            "No settings module given. Set APP_SETTINGS_MODULE "
            "(e.g. config.DevelopConfig) or pass a config class to create_app()."
        )

    app = Flask(__name__)
    app.config.from_object(settings_module)

    # Trust X-Forwarded-* from the configured number of reverse proxies so that
    # request.remote_addr (logs, rate limiting) is the real client address.
    proxies = app.config["TRUSTED_PROXY_COUNT"]
    if proxies > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies
        )

    # Initialize the extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    # No CORS headers at all unless origins are configured. Credentials are not
    # needed: authentication is a bearer token, not a cookie.
    if app.config["CORS_ORIGINS"]:
        cors.init_app(
            app, origins=app.config["CORS_ORIGINS"], supports_credentials=False
        )
    manage.init_app(app)

    # Logging configuration
    configure_logging(app)

    # Register Blueprint
    register_routing(app)

    # Unhandled exceptions: log the traceback, answer with a generic JSON 500
    # (flask-smorest only formats HTTPExceptions). Not used when the app is
    # in TESTING / DEBUG mode, where exceptions propagate instead.
    app.register_error_handler(InternalServerError, _handle_internal_error)

    return app


def _handle_internal_error(error):
    logger.exception(
        "Unhandled exception", exc_info=getattr(error, "original_exception", error)
    )
    return (
        jsonify(
            {
                "code": 500,
                "status": "Internal Server Error",
                "message": "Internal error.",
            }
        ),
        500,
    )
