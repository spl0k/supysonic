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

from flask import session, request, redirect, url_for
from supysonic.web import app, store
from supysonic.db import Artist, Album, Track
from supysonic.managers.user import UserManager
from functools import wraps

@app.before_request
def login_check():
    if request.path.startswith('/rest/'):
        return

    if request.path.startswith('/static/'):
        return

    request.user = None
    should_login = True
    if session.get('userid'):
        code, user = UserManager.get(store, session.get('userid'))
        if code != UserManager.SUCCESS:
            session.clear()
        else:
            request.user = user
            should_login = False

    if should_login and request.endpoint != 'login':
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

def admin_only(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not request.user or not request.user.admin:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_func

from .user import *
from .folder import *
from .playlist import *
