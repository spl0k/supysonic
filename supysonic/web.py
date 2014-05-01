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
from flask import Flask

from supysonic import config

def teardown(exception):
	db.session.remove()

def create_application():
	global app, db, UserManager

	if not config.check():
		return None

	if not os.path.exists(config.get('base', 'cache_dir')):
		os.makedirs(config.get('base', 'cache_dir'))

	from supysonic import db
	db.init_db()

	app = Flask(__name__)
	app.secret_key = '?9huDM\\H'

	if config.get('base', 'log_file'):
		import logging
		from logging.handlers import TimedRotatingFileHandler
		handler = TimedRotatingFileHandler(config.get('base', 'log_file'), when = 'midnight')
		handler.setLevel(logging.WARNING)
		app.logger.addHandler(handler)

	app.teardown_request(teardown)

	from supysonic import frontend
	from supysonic import api

	return app

