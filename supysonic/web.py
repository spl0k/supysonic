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

from flask import Flask, g
from os import makedirs, path
from werkzeug.local import LocalProxy

from supysonic import config
from supysonic.db import get_store

# Supysonic database open
def get_db():
    if not hasattr(g, 'database'):
        g.database = get_store(config.get('base', 'database_uri'))
    return g.database

# Supysonic database close
def close_db(error):
    if hasattr(g, 'database'):
        g.database.close()

store = LocalProxy(get_db)

def create_application():
    global app

    # Check config for mandatory fields
    config.check()

    # Test for the cache directory
    if not path.exists(config.get('webapp', 'cache_dir')):
        os.makedirs(config.get('webapp', 'cache_dir'))

    # Flask!
    app = Flask(__name__)

    # Set a secret key for sessions
    secret_key = config.get('base', 'secret_key')
    # If secret key is not defined in config, set develop key
    if secret_key is None:
        app.secret_key = 'd3v3l0p'
    else:
        app.secret_key = secret_key

    # Close database connection on teardown
    app.teardown_appcontext(close_db)

    # Set loglevel
    if config.get('webapp', 'log_file'):
        import logging
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(config.get('webapp', 'log_file'), when = 'midnight')
        if config.get('webapp', 'log_level'):
            mapping = {
                'DEBUG':   logging.DEBUG,
                'INFO':    logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR':   logging.ERROR,
                'CRTICAL': logging.CRITICAL
            }
            handler.setLevel(mapping.get(config.get('webapp', 'log_level').upper(), logging.NOTSET))
        app.logger.addHandler(handler)

    # Import app sections
    from supysonic import frontend
    from supysonic import api

    return app
