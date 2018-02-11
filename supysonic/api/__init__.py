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

API_VERSION = '1.8.0'

import binascii
import uuid

from flask import request
from flask import Blueprint
from pony.orm import db_session, ObjectNotFound

from ..managers.user import UserManager
from ..py23 import dict

from .formatters import JSONFormatter, JSONPFormatter, XMLFormatter

api = Blueprint('api', __name__)

@api.before_request
def set_formatter():
    """Return a function to create the response."""
    f, callback = map(request.values.get, ['f', 'callback'])
    if f == 'jsonp':
        request.formatter = JSONPFormatter(callback)
    elif f == 'json':
        request.formatter = JSONFormatter()
    else:
        request.formatter = XMLFormatter()

def decode_password(password):
    if not password.startswith('enc:'):
        return password

    try:
        return binascii.unhexlify(password[4:].encode('utf-8')).decode('utf-8')
    except:
        return password

@api.before_request
def authorize():
    error = request.formatter.error(40, 'Unauthorized'), 401

    if request.authorization:
        status, user = UserManager.try_auth(request.authorization.username, request.authorization.password)
        if status == UserManager.SUCCESS:
            request.username = request.authorization.username
            request.user = user
            return

    (username, password) = map(request.values.get, [ 'u', 'p' ])
    if not username or not password:
        return error

    password = decode_password(password)
    status, user = UserManager.try_auth(username, password)
    if status != UserManager.SUCCESS:
        return error

    request.username = username
    request.user = user

@api.before_request
def get_client_prefs():
    if 'c' not in request.values:
        return request.formatter.error(10, 'Missing required parameter')

    client = request.values.get('c')
    with db_session:
        try:
            ClientPrefs[request.user.id, client]
        except ObjectNotFound:
            ClientPrefs(user = User[request.user.id], client_name = client)

    request.client = client

#@api.errorhandler(404)
@api.route('/<path:invalid>', methods = [ 'GET', 'POST' ]) # blueprint 404 workaround
def not_found(*args, **kwargs):
    return request.formatter.error(0, 'Not implemented'), 501

def get_entity(cls, param = 'id'):
    eid = request.values.get(param)
    if not eid:
        return False, request.formatter.error(10, 'Missing %s id' % cls.__name__)

    try:
        eid = uuid.UUID(eid)
        entity = cls[eid]
        return True, entity
    except ValueError:
        return False, request.formatter.error(0, 'Invalid %s id' % cls.__name__)
    except ObjectNotFound:
        return False, (request.formatter.error(70, '%s not found' % cls.__name__), 404)

from .system import *
from .browse import *
from .user import *
from .albums_songs import *
from .media import *
from .annotation import *
from .chat import *
from .search import *
from .playlists import *

