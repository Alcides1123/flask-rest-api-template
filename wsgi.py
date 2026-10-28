"""
WSGI entrypoint.

    gunicorn wsgi:app            (production / docker, see entrypoint.sh)
    flask run                    (the Flask CLI discovers this file automatically)

The configuration class is taken from the APP_SETTINGS_MODULE environment
variable, e.g. "config.DevelopConfig". Nothing is created at import time
anywhere else in the package, so tests can build their own app instances with
app.create_app(...) without side effects.
"""
import os

from app import create_app

app = create_app(os.getenv("APP_SETTINGS_MODULE"))
