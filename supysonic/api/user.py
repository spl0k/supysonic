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

from flask import request
from supysonic.web import app, store
from supysonic.db import User
from supysonic.managers.user import UserManager

@app.route('/rest/getUser.view', methods = [ 'GET', 'POST' ])
def user_info():
	username = request.values.get('username')
	if username is None:
		return request.error_formatter(10, 'Missing username')

	if username != request.username and not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	user = store.find(User, User.name == username).one()
	if user is None:
		return request.error_formatter(0, 'Unknown user')

	return request.formatter({ 'user': user.as_subsonic_user() })

@app.route('/rest/getUsers.view', methods = [ 'GET', 'POST' ])
def users_info():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	return request.formatter({ 'users': { 'user': [ u.as_subsonic_user() for u in store.find(User) ] } })

@app.route('/rest/createUser.view', methods = [ 'GET', 'POST' ])
def user_add():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	username, password, email, admin = map(request.values.get, [ 'username', 'password', 'email', 'adminRole' ])
	if not username or not password or not email:
		return request.error_formatter(10, 'Missing parameter')
	admin = True if admin in (True, 'True', 'true', 1, '1') else False

	status = UserManager.add(store, username, password, email, admin)
	if status == UserManager.NAME_EXISTS:
		return request.error_formatter(0, 'There is already a user with that username')

	return request.formatter({})

@app.route('/rest/deleteUser.view', methods = [ 'GET', 'POST' ])
def user_del():
	if not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	username = request.values.get('username')
	user = store.find(User, User.name == username).one()
	if not user:
		return request.error_formatter(70, 'Unknown user')

	status = UserManager.delete(store, user.id)
	if status != UserManager.SUCCESS:
		return request.error_formatter(0, UserManager.error_str(status))

	return request.formatter({})

@app.route('/rest/changePassword.view', methods = [ 'GET', 'POST' ])
def user_changepass():
	username, password = map(request.values.get, [ 'username', 'password' ])
	if not username or not password:
		return request.error_formatter(10, 'Missing parameter')

	if username != request.username and not request.user.admin:
		return request.error_formatter(50, 'Admin restricted')

	status = UserManager.change_password2(store, username, password)
	if status != UserManager.SUCCESS:
		return request.error_formatter(0, UserManager.error_str(status))

	return request.formatter({})

