# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2014  Alban 'spl0k' Féron
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

from flask import session
from web import app, store
from db import Artist, Album, Track
from managers.user import UserManager

app.add_template_filter(str)

@app.before_request
def login_check():
	if request.path.startswith('/rest/'):
		return

	if request.endpoint != 'login':
		should_login = False
		if not session.get('userid'):
			should_login = True
		elif UserManager.get(store, session.get('userid'))[0] != UserManager.SUCCESS:
			session.clear()
			should_login = True

		if should_login:
			flash('Please login')
			return redirect(url_for('login', returnUrl = request.script_root + request.url[len(request.url_root)-1:]))

@app.route('/')
def index():
	stats = {
		'artists': store.find(Artist).count(),
		'albums': store.find(Album).count(),
		'tracks': store.find(Track).count()
	}
	return render_template('home.html', stats = stats, admin = UserManager.get(store, session.get('userid'))[1].admin)

from .user import *
from .folder import *
from .playlist import *

