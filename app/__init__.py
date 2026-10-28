import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

import manage
from app.blueprint import register_routing
from app.db import db
from app.extention import cors, limiter, migrate
from app.utils.auth import jwt
from app.utils.logging import configure_logging


def create_app(settings_module):
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

    return app


settings_module = os.getenv("APP_SETTINGS_MODULE")
app = create_app(settings_module)
