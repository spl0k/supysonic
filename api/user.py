# coding: utf-8

from flask import request
from web import app
from db import User
from managers.user import UserManager

@app.route('/rest/getUser.view', methods = [ 'GET', 'POST' ])
def user_info():
	username = request.args.get('username')
	if username is None:
		return request.error_formatter(10, 'Missing username')

	if username != request.username and not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	user = User.query.filter(User.name == username).first()
	if user is None:
		return request.error_formatter(0, 'Unknown user')

	return request.formatter({ 'user': user.as_subsonic_user() })

@app.route('/rest/getUsers.view', methods = [ 'GET', 'POST' ])
def users_info():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	return request.formatter({ 'users': { 'user': [ u.as_subsonic_user() for u in User.query.all() ] } })

@app.route('/rest/createUser.view', methods = [ 'GET', 'POST' ])
def user_add():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	username, password, email, admin = map(request.args.get, [ 'username', 'password', 'email', 'adminRole' ])
	if not username or not password or not email:
		return request.error_formatter(10, 'Missing parameter')
	admin = True if admin in (True, 'True', 'true', 1, '1') else False

	status = UserManager.add(username, password, email, admin)
	if status == UserManager.NAME_EXISTS:
		return request.error_formatter(0, 'There is already a user with that username')

	return request.formatter({})

@app.route('/rest/deleteUser.view', methods = [ 'GET', 'POST' ])
def user_del():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	username = request.args.get('username')
	user = User.query.filter(User.name == username).first()
	if not user:
		return request.error_formatter(70, 'Unknown user')

	status = UserManager.delete(user.id)
	if status != UserManager.SUCCESS:
		return request.error_formatter(0, UserManager.error_str(status))

	return request.formatter({})

@app.route('/rest/changePassword.view', methods = [ 'GET', 'POST' ])
def user_changepass():
	username, password = map(request.args.get, [ 'username', 'password' ])
	if not username or not password:
		return request.error_formatter(10, 'Missing parameter')

	if username != request.username and not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	status = UserManager.change_password2(username, password)
	if status != UserManager.SUCCESS:
		return request.error_formatter(0, UserManager.error_str(status))

	return request.formatter({})

