import logging
import os
from datetime import datetime

import pytz
from flask import Flask

# Marker attribute so that configure_logging() can find (and replace) the
# handlers it added on a previous call instead of stacking duplicates.
_HANDLER_TAG = "_flask_template_handler"


class TimezoneFormatter(logging.Formatter):
    """
    Formatter that renders timestamps in a configurable timezone, without
    monkey-patching logging.Formatter.converter for the whole process.
    """

    def __init__(self, fmt, datefmt, timezone):
        super().__init__(fmt, datefmt)
        self.timezone = pytz.timezone(timezone)

    def converter(self, timestamp):
        return datetime.fromtimestamp(timestamp, self.timezone).timetuple()


def configure_logging(app: Flask):
    """
    Log to the console and to app.config["LOG_FILE_API"].

    Idempotent: calling it again (e.g. every test builds a new app) replaces
    the handlers from the previous call instead of adding more.
    """
    logger = logging.getLogger(app.name)
    logger.setLevel(logging.DEBUG)

    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_TAG, False):
            logger.removeHandler(handler)
            handler.close()

    timezone = app.config["LOG_TIMEZONE"]
    date_fmt = app.config["DATE_FMT"]
    console_log_format = "%(asctime)s - %(levelname)s - %(message)s"
    file_log_format = (
        "%(asctime)s - %(levelname)s - %(message)s - (%(filename)s:%(lineno)d)"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        TimezoneFormatter(console_log_format, date_fmt, timezone)
    )

    log_file = app.config["LOG_FILE_API"]
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(filename=log_file, encoding="utf-8")
    file_handler.setFormatter(TimezoneFormatter(file_log_format, date_fmt, timezone))

    for handler in (console_handler, file_handler):
        handler.setLevel(logging.DEBUG)
        setattr(handler, _HANDLER_TAG, True)
        logger.addHandler(handler)
