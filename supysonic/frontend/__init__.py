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

from flask import session
from supysonic.web import app, store
from supysonic.db import Artist, Album, Track
from supysonic.managers.user import UserManager

app.add_template_filter(str)

@app.before_request
def login_check():
    if request.path.startswith('/rest/'):
        return

    if request.path.startswith('/static/'):
        return

    if request.endpoint != 'login':
        should_login = False
        if not session.get('userid'):
            should_login = True
        elif UserManager.get(store, session.get('userid'))[0] != UserManager.SUCCESS:
            session.clear()
            should_login = True
        elif UserManager.get(store, session.get('userid'))[1].name != session.get('username'):
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
