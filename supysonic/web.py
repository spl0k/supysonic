#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright © 2013-2017 Alban 'spl0k' Féron
#                  2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
from flask import Flask, g
from werkzeug.local import LocalProxy

from supysonic import config
from supysonic.db import get_store

def get_db_store():
    store = getattr(g, 'store', None)
    if store:
        return store
    g.store = get_store(config.get('base', 'database_uri'))
    return g.store

store = LocalProxy(get_db_store)

def teardown_db(exception):
    store = getattr(g, 'store', None)
    if store:
        store.close()

def create_application():
    global app

    if not config.check():
        return None

    if not os.path.exists(config.get('webapp', 'cache_dir')):
        os.makedirs(config.get('webapp', 'cache_dir'))

    app = Flask(__name__)
    app.secret_key = '?9huDM\\H'

    app.teardown_appcontext(teardown_db)

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

    from supysonic import frontend
    from supysonic import api

    return app

