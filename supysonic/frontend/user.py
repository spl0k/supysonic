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

from flask import request, session, flash, render_template, redirect, url_for, make_response

from supysonic.web import app, store
from supysonic.managers.user import UserManager
from supysonic.db import User, ClientPrefs
import uuid, csv
from supysonic import config
from supysonic.lastfm import LastFm

@app.before_request
def check_admin():
	if not request.path.startswith('/user'):
		return

	if request.endpoint in ('user_index', 'add_user', 'del_user', 'export_users', 'import_users', 'do_user_import') and not UserManager.get(store, session.get('userid'))[1].admin:
		return redirect(url_for('index'))

@app.route('/user')
def user_index():
	return render_template('users.html', users = store.find(User), admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/<uid>')
def user_profile(uid):
	if uid == 'me':
		prefs = store.find(ClientPrefs, ClientPrefs.user_id == uuid.UUID(session.get('userid')))
		return render_template('profile.html', user = UserManager.get(store, session.get('userid'))[1], api_key = config.get('lastfm', 'api_key'), clients = prefs, admin = UserManager.get(store, session.get('userid'))[1].admin)
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		prefs = store.find(ClientPrefs, ClientPrefs.user_id == uuid.UUID(uid))
		return render_template('profile.html', user = UserManager.get(store, uid)[1], api_key = config.get('lastfm', 'api_key'), clients = prefs, admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/<uid>', methods = [ 'POST' ])
def update_clients(uid):
	clients_opts = {}
	for client in set(map(lambda k: k.rsplit('_', 1)[0], request.form.keys())):
		clients_opts[client] = { k.rsplit('_', 1)[1]: v for k, v in filter(lambda (k, v): k.startswith(client), request.form.iteritems()) }
	app.logger.debug(clients_opts)

	if uid == 'me':
		userid = uuid.UUID(session.get('userid'))
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		userid = uuid.UUID(uid)

	for client, opts in clients_opts.iteritems():
		prefs = store.get(ClientPrefs, (userid, client))
		if 'delete' in opts and opts['delete'] in [ 'on', 'true', 'checked', 'selected', '1' ]:
			store.remove(prefs)
			continue

		prefs.format  =     opts['format']   if 'format'  in opts and opts['format']  else None
		prefs.bitrate = int(opts['bitrate']) if 'bitrate' in opts and opts['bitrate'] else None

	store.commit()
	flash('Clients preferences updated.')
	return user_profile(uid)

@app.route('/user/<uid>/changeusername', methods = [ 'GET', 'POST' ])
def change_username(uid):
    if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
        return redirect(url_for('index'))
    user = UserManager.get(store, uid)[1]
    if request.method == 'POST':
        username = request.form.get('user')
        if username in ('', None):
            flash('The username is required')
            return render_template('change_username.html', user = user, admin = UserManager.get(store, session.get('userid'))[1].admin)
        if request.form.get('admin') is None:
            admin = False
        else:
            admin = True
        changed = False
        if user.name != username or user.admin != admin:
            user.name = username
            user.admin = admin
            store.commit()
            flash("User '%s' updated." % username)
            return redirect(url_for('user_profile', uid = uid))
        else:
            flash("No changes for '%s'." % username)
            return redirect(url_for('user_profile', uid = uid))

    return render_template('change_username.html', user = user, admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/<uid>/changemail', methods = [ 'GET', 'POST' ])
def change_mail(uid):
	if uid == 'me':
		user = UserManager.get(store, session.get('userid'))[1]
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		user = UserManager.get(store, uid)[1]
	if request.method == 'POST':
		mail = request.form.get('mail')
		# No validation, lol.
		user.mail = mail
		store.commit()
		return redirect(url_for('user_profile', uid = uid))

	return render_template('change_mail.html', user = user, admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/<uid>/changepass', methods = [ 'GET', 'POST' ])
def change_password(uid):
	if uid == 'me':
		user = UserManager.get(store, session.get('userid'))[1].name
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		user = UserManager.get(store, uid)[1].name
	if request.method == 'POST':
		error = False
		if uid == 'me' or uid == session.get('userid'):
			current, new, confirm = map(request.form.get, [ 'current', 'new', 'confirm' ])
			if current in ('', None):
				flash('The current password is required')
				error = True
		else:
			new, confirm = map(request.form.get, [ 'new', 'confirm' ])
		if new in ('', None):
			flash('The new password is required')
			error = True
		if new != confirm:
			flash("The new password and its confirmation don't match")
			error = True

		if not error:
			if uid == 'me' or uid == session.get('userid'):
				status = UserManager.change_password(store, session.get('userid'), current, new)
			else:
				status = UserManager.change_password2(store, UserManager.get(store, uid)[1].name, new)
			if status != UserManager.SUCCESS:
				flash(UserManager.error_str(status))
			else:
				flash('Password changed')
				return redirect(url_for('user_profile', uid = uid))

	return render_template('change_pass.html', user = user, admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/add', methods = [ 'GET', 'POST' ])
def add_user():
	if request.method == 'GET':
		return render_template('adduser.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

	error = False
	(name, passwd, passwd_confirm, mail, admin) = map(request.form.get, [ 'user', 'passwd', 'passwd_confirm', 'mail', 'admin' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	if passwd in (None, ''):
		flash('Please provide a password.')
		error = True
	elif passwd != passwd_confirm:
		flash("The passwords don't match.")
		error = True

	if admin is None:
		admin = True if store.find(User, User.admin == True).count() == 0 else False
	else:
		admin = True

	if not error:
		status = UserManager.add(store, name, passwd, mail, admin)
		if status == UserManager.SUCCESS:
			flash("User '%s' successfully added" % name)
			return redirect(url_for('user_index'))
		else:
			flash(UserManager.error_str(status))

	return render_template('adduser.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/del/<uid>')
def del_user(uid):
	status = UserManager.delete(store, uid)
	if status == UserManager.SUCCESS:
		flash('Deleted user')
	else:
		flash(UserManager.error_str(status))

	return redirect(url_for('user_index'))

@app.route('/user/export')
def export_users():
	resp = make_response('\n'.join([ '%s,%s,%s,%s,"%s",%s,%s,%s' % (u.id, u.name, u.mail, u.password, u.salt, u.admin, u.lastfm_session, u.lastfm_status)
		for u in store.find(User) ]))
	resp.headers['Content-disposition'] = 'attachment;filename=users.csv'
	resp.headers['Content-type'] = 'text/csv'
	return resp

@app.route('/user/import')
def import_users():
	return render_template('importusers.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/user/import', methods = [ 'POST' ])
def do_user_import():
	if not request.files['file']:
		return render_template('importusers.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

	users = []
	reader = csv.reader(request.files['file'])
	for id, name, mail, password, salt, admin, lfmsess, lfmstatus in reader:
		mail = None if mail == 'None' else mail
		admin = admin == 'True'
		lfmsess = None if lfmsess == 'None' else lfmsess
		lfmstatus = lfmstatus == 'True'

		user = User()
		user.id = uuid.UUID(id)
		user.name = name
		user.password = password
		user.salt = salt
		user.admin = admin
		user.lastfm_session = lfmsess
		user.lastfm_status = lfmstatus

		users.append(user)

	store.find(User).remove()
	for u in users:
		store.add(u)
	store.commit()

	return redirect(url_for('user_index'))

@app.route('/user/<uid>/lastfm/link')
def lastfm_reg(uid):
	token = request.args.get('token')
	if token in ('', None):
		flash('Missing LastFM auth token')
		return redirect(url_for('user_profile', uid = uid))

	if uid == 'me':
		lfm = LastFm(UserManager.get(store, session.get('userid'))[1], app.logger)
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		lfm = LastFm(UserManager.get(store, uid)[1], app.logger)
	status, error = lfm.link_account(token)
	store.commit()
	flash(error if not status else 'Successfully linked LastFM account')

	return redirect(url_for('user_profile', uid = uid))

@app.route('/user/<uid>/lastfm/unlink')
def lastfm_unreg(uid):
	if uid == 'me':
		lfm = LastFm(UserManager.get(store, session.get('userid'))[1], app.logger)
	else:
		if not UserManager.get(store, session.get('userid'))[1].admin or not UserManager.get(store, uid)[0] is UserManager.SUCCESS:
			return redirect(url_for('index'))
		lfm = LastFm(UserManager.get(store, uid)[1], app.logger)
	lfm.unlink_account()
	store.commit()
	flash('Unliked LastFM account')
	return redirect(url_for('user_profile', uid = uid))

@app.route('/user/login', methods = [ 'GET', 'POST'])
def login():
	return_url = request.args.get('returnUrl') or url_for('index')
	if session.get('userid'):
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
		status, user = UserManager.try_auth(store, name, password)
		if status == UserManager.SUCCESS:
			session['userid'] = str(user.id)
			session['username'] = user.name
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

