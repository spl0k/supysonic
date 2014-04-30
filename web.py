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

from flask import Flask

from flask.ext.sqlalchemy import SQLAlchemy
import os.path
import config

if not config.check():
    exit

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

app_db = SQLAlchemy(app)

if(config.get('base', 'accel-redirect')):
    app.use_x_sendfile = True

if not os.path.exists(config.get('base', 'cache_dir')):
    os.makedirs(config.get('base', 'cache_dir'))

if config.get('base', 'debug'):
    app.debug = True
    app.config['SQLALCHEMY_ECHO'] = "debug"

if config.get('base', 'log_file'):
    import logging
    from logging.handlers import TimedRotatingFileHandler
    handler = TimedRotatingFileHandler(config.get('base', 'log_file'), when = 'midnight', encoding = 'UTF-8')
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)

app.config['SQLALCHEMY_DATABASE_URI'] = config.get('base',  'database_uri')
