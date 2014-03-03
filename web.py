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

import config

def login_check():
	if request.path.startswith('/rest/'):
		return

	if request.endpoint != 'login':
		should_login = False
		if not session.get('userid'):
			should_login = True
		elif UserManager.get(session.get('userid'))[0] != UserManager.SUCCESS:
			session.clear()
			should_login = True

		if should_login:
			flash('Please login')
			return redirect(url_for('login', returnUrl = request.script_root + request.url[len(request.url_root)-1:]))

def teardown(exception):
	db.session.remove()

def index():
	stats = {
		'artists': db.Artist.query.count(),
		'albums': db.Album.query.count(),
		'tracks': db.Track.query.count()
	}
	return render_template('home.html', stats = stats, admin = UserManager.get(session.get('userid'))[1].admin)

def create_application():
	global app, db, UserManager

	if not config.check():
		return None

	if not os.path.exists(config.get('base', 'cache_dir')):
		os.makedirs(config.get('base', 'cache_dir'))

	import db
	db.init_db()

	app = Flask(__name__)
	app.secret_key = '?9huDM\\H'

	if config.get('base', 'log_file'):
		import logging
		from logging.handlers import TimedRotatingFileHandler
		handler = TimedRotatingFileHandler(config.get('base', 'log_file'), when = 'midnight')
		handler.setLevel(logging.WARNING)
		app.logger.addHandler(handler)

	from managers.user import UserManager

	app.before_request(login_check)
	app.teardown_request(teardown)
	app.add_template_filter(str)
	app.add_url_rule('/', view_func = index)

	import user
	import folder
	import playlist

	import api.system
	import api.browse
	import api.user
	import api.albums_songs
	import api.media
	import api.annotation
	import api.chat
	import api.search
	import api.playlists

	return app

