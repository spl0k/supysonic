# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import logging
import mimetypes

from flask import Flask
from os import makedirs, path, urandom
from pony.orm import db_session

from .config import IniConfig
from .db import init_database

logger = logging.getLogger(__package__)

def create_application(config = None):
    global app

    # Flask!
    app = Flask(__name__)
    app.config.from_object('supysonic.config.DefaultConfig')

    if not config: # pragma: nocover
        config = IniConfig.from_common_locations()
    app.config.from_object(config)

    # Set loglevel
    logfile = app.config['WEBAPP']['log_file']
    if logfile: # pragma: nocover
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(logfile, when = 'midnight')
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    loglevel = app.config['WEBAPP']['log_level']
    if loglevel:
        logger.setLevel(getattr(logging, loglevel.upper(), logging.NOTSET))

    # Initialize database
    init_database(app.config['BASE']['database_uri'])
    app.wsgi_app = db_session(app.wsgi_app)

    # Insert unknown mimetypes
    for k, v in app.config['MIMETYPES'].items():
        extension = '.' + k.lower()
        if extension not in mimetypes.types_map:
            mimetypes.add_type(v, extension, False)

    # Test for the cache directory
    cache_path = app.config['WEBAPP']['cache_dir']
    if not path.exists(cache_path):
        makedirs(cache_path) # pragma: nocover

    # Read or create secret key
    secret_path = path.join(cache_path, 'secret')
    if path.exists(secret_path):
        with io.open(secret_path, 'rb') as f:
            app.secret_key = f.read()
    else:
        secret = urandom(128)
        with io.open(secret_path, 'wb') as f:
            f.write(secret)
        app.secret_key = secret

    # Import app sections
    if app.config['WEBAPP']['mount_webui']:
        from .frontend import frontend
        app.register_blueprint(frontend)
    if app.config['WEBAPP']['mount_api']:
        from .api import api
        app.register_blueprint(api, url_prefix = '/rest')

    return app

