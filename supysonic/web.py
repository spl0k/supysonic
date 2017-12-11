# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import mimetypes

from flask import Flask, g, current_app
from os import makedirs, path
from werkzeug.local import LocalProxy

from .config import IniConfig
from .db import get_store

# Supysonic database open
def get_db():
    if not hasattr(g, 'database'):
        g.database = get_store(current_app.config['BASE']['database_uri'])
    return g.database

# Supysonic database close
def close_db(error):
    if hasattr(g, 'database'):
        g.database.close()

store = LocalProxy(get_db)

def create_application(config = None):
    global app

    # Flask!
    app = Flask(__name__)
    app.config.from_object('supysonic.config.DefaultConfig')

    if not config:
        config = IniConfig.from_common_locations()
    app.config.from_object(config)

    # Close database connection on teardown
    app.teardown_appcontext(close_db)

    # Set loglevel
    logfile = app.config['WEBAPP']['log_file']
    if logfile:
        import logging
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(logfile, when = 'midnight')
        loglevel = app.config['WEBAPP']['log_level']
        if loglevel:
            mapping = {
                'DEBUG':   logging.DEBUG,
                'INFO':    logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR':   logging.ERROR,
                'CRTICAL': logging.CRITICAL
            }
            handler.setLevel(mapping.get(loglevel.upper(), logging.NOTSET))
        app.logger.addHandler(handler)

    # Insert unknown mimetypes
    for k, v in app.config['MIMETYPES'].iteritems():
        extension = '.' + k.lower()
        if extension not in mimetypes.types_map:
            mimetypes.add_type(v, extension, False)

    # Test for the cache directory
    cache_path = app.config['WEBAPP']['cache_dir']
    if not path.exists(cache_path):
        makedirs(cache_path)

    # Import app sections
    with app.app_context():
        if app.config['WEBAPP']['mount_webui']:
            from . import frontend
        if app.config['WEBAPP']['mount_api']:
            from . import api

    return app

