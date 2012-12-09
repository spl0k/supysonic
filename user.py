# coding: utf-8

from flask import request, session, flash, render_template, redirect, url_for

from web import app
from user_manager import UserManager
from db import User

@app.before_request
def check_admin():
	if not request.path.startswith('/user') or request.endpoint in ('login', 'logout'):
		return

	if request.endpoint == 'add_user' and User.query.filter(User.admin == True).count() == 0:
		return

	if request.endpoint in ('user_index', 'add_user', 'del_user') and not UserManager.get(session.get('userid'))[1].admin:
		return redirect(url_for('index'))

@app.route('/user')
def user_index():
	return render_template('users.html', users = User.query.all())

@app.route('/user/add', methods = [ 'GET', 'POST' ])
def add_user():
	if request.method == 'GET':
		return render_template('adduser.html')

	error = False
	(name, passwd, passwd_confirm, mail, admin) = map(request.form.get, [ 'name', 'passwd', 'passwd_confirm', 'mail', 'admin' ])
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
		admin = True if User.query.filter(User.admin == True).count() == 0 else False
	else:
		admin = True

	if not error:
		status = UserManager.add(name, passwd, mail, admin)
		if status == UserManager.SUCCESS:
			flash("User '%s' successfully added" % name)
			return redirect(url_for('user_index'))
		else:
			flash(UserManager.error_str(status))

	return render_template('adduser.html')


@app.route('/user/del/<uid>')
def del_user(uid):
	status = UserManager.delete(uid)
	if status == UserManager.SUCCESS:
		flash('Deleted user')
	else:
		flash(UserManager.error_str(status))

	return redirect(url_for('user_index'))

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

