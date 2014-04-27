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
from flask import Flask, request, session, flash, render_template, redirect, url_for
import db
import config

def teardown(exception):
	db.session.remove()


def create_application():
    if not config.check():
        return None

    app = Flask(__name__)
    app.secret_key = '?9huDM\\H'

    if(config.get('base', 'accel-redirect')):
        app.use_x_sendfile = True

    if not os.path.exists(str(config.get('base', 'cache_dir'))):
            os.makedirs(config.get('base', 'cache_dir'))

    if config.get('base', 'debug'):
        app.debug = True
        app.config['SQLALCHEMY_ECHO'] = True

    if config.get('base', 'log_file'):
        import logging
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(config.get('base', 'log_file'), when = 'midnight', encoding = 'UTF-8')
        handler.setLevel(logging.DEBUG)
        app.logger.addHandler(handler)

    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('base',  'database_uri')

    db.database.init_app(app)

    app.teardown_request(teardown)

    return app

app = create_application()

with app.app_context():
    db.init_db()

@app.template_filter('str')
def to_string(obj):
	return str(obj)


