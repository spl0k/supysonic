# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2017  Alban 'spl0k' Féron
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

from flask import request, session, flash, render_template, redirect, url_for, current_app as app
from functools import wraps
from pony.orm import db_session

from ..db import User, ClientPrefs
from ..lastfm import LastFm
from ..managers.user import UserManager

from . import admin_only

def me_or_uuid(f, arg = 'uid'):
    @db_session
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if kwargs:
            uid = kwargs[arg]
        else:
            uid = args[0]

        if uid == 'me':
            user = User[request.user.id] # Refetch user from previous transaction
        elif not request.user.admin:
            return redirect(url_for('index'))
        else:
            code, user = UserManager.get(uid)
            if code != UserManager.SUCCESS:
                flash(UserManager.error_str(code))
                return redirect(url_for('index'))

        if kwargs:
            kwargs['user'] = user
        else:
            args = (uid, user)

        return f(*args, **kwargs)

    return decorated_func

@app.route('/user')
@admin_only
@db_session
def user_index():
    return render_template('users.html', users = User.select())

@app.route('/user/<uid>')
@me_or_uuid
def user_profile(uid, user):
    return render_template('profile.html', user = user, has_lastfm = app.config['LASTFM']['api_key'] != None, clients = user.clients)

@app.route('/user/<uid>', methods = [ 'POST' ])
@me_or_uuid
def update_clients(uid, user):
    clients_opts = {}
    for key, value in request.form.iteritems():
        if '_' not in key:
            continue
        parts = key.split('_')
        if len(parts) != 2:
            continue
        client, opt = parts
        if not client or not opt:
            continue

        if client not in clients_opts:
            clients_opts[client] = { opt: value }
        else:
            clients_opts[client][opt] = value
    app.logger.debug(clients_opts)

    for client, opts in clients_opts.iteritems():
        prefs = user.clients.select(lambda c: c.client_name == client).first()
        if prefs is None:
            continue

        if 'delete' in opts and opts['delete'] in [ 'on', 'true', 'checked', 'selected', '1' ]:
            prefs.delete()
            continue

        prefs.format  =     opts['format']   if 'format'  in opts and opts['format']  else None
        prefs.bitrate = int(opts['bitrate']) if 'bitrate' in opts and opts['bitrate'] else None

    flash('Clients preferences updated.')
    return user_profile(uid, user)

@app.route('/user/<uid>/changeusername')
@admin_only
def change_username_form(uid):
    code, user = UserManager.get(uid)
    if code != UserManager.SUCCESS:
        flash(UserManager.error_str(code))
        return redirect(url_for('index'))

    return render_template('change_username.html', user = user)

@app.route('/user/<uid>/changeusername', methods = [ 'POST' ])
@admin_only
@db_session
def change_username_post(uid):
    code, user = UserManager.get(uid)
    if code != UserManager.SUCCESS:
        return redirect(url_for('index'))

    username = request.form.get('user')
    if username in ('', None):
        flash('The username is required')
        return render_template('change_username.html', user = user)
    if user.name != username and User.get(name = username) is not None:
        flash('This name is already taken')
        return render_template('change_username.html', user = user)

    if request.form.get('admin') is None:
        admin = False
    else:
        admin = True

    if user.name != username or user.admin != admin:
        user.name = username
        user.admin = admin
        flash("User '%s' updated." % username)
    else:
        flash("No changes for '%s'." % username)

    return redirect(url_for('user_profile', uid = uid))

@app.route('/user/<uid>/changemail')
@me_or_uuid
def change_mail_form(uid, user):
    return render_template('change_mail.html', user = user)

@app.route('/user/<uid>/changemail', methods = [ 'POST' ])
@me_or_uuid
def change_mail_post(uid, user):
    mail = request.form.get('mail', '')
    # No validation, lol.
    user.mail = mail
    return redirect(url_for('user_profile', uid = uid))

@app.route('/user/<uid>/changepass')
@me_or_uuid
def change_password_form(uid, user):
    return render_template('change_pass.html', user = user)

@app.route('/user/<uid>/changepass', methods = [ 'POST' ])
@me_or_uuid
def change_password_post(uid, user):
    error = False
    if user.id == request.user.id:
        current = request.form.get('current')
        if not current:
            flash('The current password is required')
            error = True

    new, confirm = map(request.form.get, [ 'new', 'confirm' ])

    if not new:
        flash('The new password is required')
        error = True
    if new != confirm:
        flash("The new password and its confirmation don't match")
        error = True

    if not error:
        if user.id == request.user.id:
            status = UserManager.change_password(user.id, current, new)
        else:
            status = UserManager.change_password2(user.name, new)

        if status != UserManager.SUCCESS:
            flash(UserManager.error_str(status))
        else:
            flash('Password changed')
            return redirect(url_for('user_profile', uid = uid))

    return change_password_form(uid, user)

@app.route('/user/add')
@admin_only
def add_user_form():
    return render_template('adduser.html')

@app.route('/user/add', methods = [ 'POST' ])
@admin_only
def add_user_post():
    error = False
    (name, passwd, passwd_confirm, mail, admin) = map(request.form.get, [ 'user', 'passwd', 'passwd_confirm', 'mail', 'admin' ])
    if not name:
        flash('The name is required.')
        error = True
    if not passwd:
        flash('Please provide a password.')
        error = True
    elif passwd != passwd_confirm:
        flash("The passwords don't match.")
        error = True

    admin = admin is not None
    if mail is None:
        mail = ''

    if not error:
        status = UserManager.add(name, passwd, mail, admin)
        if status == UserManager.SUCCESS:
            flash("User '%s' successfully added" % name)
            return redirect(url_for('user_index'))
        else:
            flash(UserManager.error_str(status))

    return add_user_form()

@app.route('/user/del/<uid>')
@admin_only
def del_user(uid):
    status = UserManager.delete(uid)
    if status == UserManager.SUCCESS:
        flash('Deleted user')
    else:
        flash(UserManager.error_str(status))

    return redirect(url_for('user_index'))

@app.route('/user/<uid>/lastfm/link')
@me_or_uuid
def lastfm_reg(uid, user):
    token = request.args.get('token')
    if token in ('', None):
        flash('Missing LastFM auth token')
        return redirect(url_for('user_profile', uid = uid))

    lfm = LastFm(app.config['LASTFM'], user, app.logger)
    status, error = lfm.link_account(token)
    flash(error if not status else 'Successfully linked LastFM account')

    return redirect(url_for('user_profile', uid = uid))

@app.route('/user/<uid>/lastfm/unlink')
@me_or_uuid
def lastfm_unreg(uid, user):
    lfm = LastFm(app.config['LASTFM'], user, app.logger)
    lfm.unlink_account()
    flash('Unlinked LastFM account')
    return redirect(url_for('user_profile', uid = uid))

@app.route('/user/login', methods = [ 'GET', 'POST'])
def login():
    return_url = request.args.get('returnUrl') or url_for('index')
    if request.user:
        flash('Already logged in')
        return redirect(return_url)

    if request.method == 'GET':
        return render_template('login.html')

    name, password = map(request.form.get, [ 'user', 'password' ])
    error = False
    if name in ('', None):
        flash('Missing user name')
        error = True
    if password in ('', None):
        flash('Missing password')
        error = True

    if not error:
        status, user = UserManager.try_auth(name, password)
        if status == UserManager.SUCCESS:
            session['userid'] = str(user.id)
            flash('Logged in!')
            return redirect(return_url)
        else:
            flash(UserManager.error_str(status))

    return render_template('login.html')

@app.route('/user/logout')
def logout():
    session.clear()
    flash('Logged out!')
    return redirect(url_for('login'))

