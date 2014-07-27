# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

