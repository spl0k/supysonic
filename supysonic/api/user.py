# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
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
from functools import wraps

from ..db import User
from ..managers.user import UserManager
from ..py23 import dict

from . import api, decode_password
from .exceptions import Forbidden, GenericError, NotFound

def admin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.user.admin:
            raise Forbidden()
        return f(*args, **kwargs)
    return decorated

@api.route('/getUser.view', methods = [ 'GET', 'POST' ])
def user_info():
    username = request.values['username']

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    user = User.get(name = username)
    if user is None:
        raise NotFound('User')

    return request.formatter('user', user.as_subsonic_user())

@api.route('/getUsers.view', methods = [ 'GET', 'POST' ])
@admin_only
def users_info():
    return request.formatter('users', dict(user = [ u.as_subsonic_user() for u in User.select() ] ))

@api.route('/createUser.view', methods = [ 'GET', 'POST' ])
@admin_only
def user_add():
    username = request.values['username']
    password = request.values['password']
    email = request.values['email']
    admin = request.values.get('adminRole')
    admin = True if admin in (True, 'True', 'true', 1, '1') else False

    password = decode_password(password)
    status = UserManager.add(username, password, email, admin)
    if status == UserManager.NAME_EXISTS:
        raise GenericError('There is already a user with that username')

    return request.formatter.empty

@api.route('/deleteUser.view', methods = [ 'GET', 'POST' ])
@admin_only
def user_del():
    username = request.values['username']

    user = User.get(name = username)
    if user is None:
        raise NotFound('User')

    status = UserManager.delete(user.id)
    if status != UserManager.SUCCESS:
        raise GenericError(UserManager.error_str(status))

    return request.formatter.empty

@api.route('/changePassword.view', methods = [ 'GET', 'POST' ])
def user_changepass():
    username = request.values['username']
    password = request.values['password']

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    password = decode_password(password)
    status = UserManager.change_password2(username, password)
    if status == UserManager.NO_SUCH_USER:
        raise NotFound('User')
    elif status != UserManager.SUCCESS:
        raise GenericError(UserManager.error_str(status))

    return request.formatter.empty

