# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import mimetypes

from flask import Flask
from os import makedirs, path

from .config import IniConfig
from .cache import Cache
from .db import init_database
from .utils import get_secret_key

logger = logging.getLogger(__package__)


def create_application(config=None):
    global app

    # Flask!
    app = Flask(__name__)
    app.config.from_object("supysonic.config.DefaultConfig")

    if not config:  # pragma: nocover
        config = IniConfig.from_common_locations()
    app.config.from_object(config)

    # Set loglevel
    logfile = app.config["WEBAPP"]["log_file"]
    if logfile:  # pragma: nocover
        from logging.handlers import TimedRotatingFileHandler

        handler = TimedRotatingFileHandler(logfile, when="midnight")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    loglevel = app.config["WEBAPP"]["log_level"]
    if loglevel:
        logger.setLevel(getattr(logging, loglevel.upper(), logging.NOTSET))

    # Initialize database
    init_database(app.config["BASE"]["database_uri"])

    # Insert unknown mimetypes
    for k, v in app.config["MIMETYPES"].items():
        extension = "." + k.lower()
        if extension not in mimetypes.types_map:
            mimetypes.add_type(v, extension, False)

    # Initialize Cache objects
    # Max size is MB in the config file but Cache expects bytes
    cache_dir = app.config["WEBAPP"]["cache_dir"]
    max_size_cache = app.config["WEBAPP"]["cache_size"] * 1024**2
    max_size_transcodes = app.config["WEBAPP"]["transcode_cache_size"] * 1024**2
    app.cache = Cache(path.join(cache_dir, "cache"), max_size_cache)
    app.transcode_cache = Cache(path.join(cache_dir, "transcodes"), max_size_transcodes)

    # Test for the cache directory
    cache_path = app.config["WEBAPP"]["cache_dir"]
    if not path.exists(cache_path):
        makedirs(cache_path)  # pragma: nocover

    # Read or create secret key
    app.secret_key = get_secret_key("cookies_secret")

    # Import app sections
    if app.config["WEBAPP"]["mount_webui"]:
        from .frontend import frontend

        app.register_blueprint(frontend)
    if app.config["WEBAPP"]["mount_api"]:
        from .api import api

        app.register_blueprint(api, url_prefix="/rest")

    return app
