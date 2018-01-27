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
from flask import current_app as app
from pony.orm import db_session, ObjectNotFound

from ..managers.user import UserManager
from ..py23 import dict

from .formatters import make_json_response, make_jsonp_response, make_xml_response
from .formatters import make_error_response_func

@app.before_request
def set_formatter():
    if not request.path.startswith('/rest/'):
        return

    """Return a function to create the response."""
    f, callback = map(request.values.get, ['f', 'callback'])
    if f == 'jsonp':
        request.formatter = lambda x, **kwargs: make_jsonp_response(x, callback, kwargs)
    elif f == 'json':
        request.formatter = make_json_response
    else:
        request.formatter = make_xml_response

    request.error_formatter = make_error_response_func(request.formatter)

def decode_password(password):
    if not password.startswith('enc:'):
        return password

    try:
        return binascii.unhexlify(password[4:].encode('utf-8')).decode('utf-8')
    except:
        return password

@app.before_request
def authorize():
    if not request.path.startswith('/rest/'):
        return

    error = request.error_formatter(40, 'Unauthorized'), 401

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

@app.before_request
def get_client_prefs():
    if not request.path.startswith('/rest/'):
        return

    if 'c' not in request.values:
        return request.error_formatter(10, 'Missing required parameter')

    client = request.values.get('c')
    with db_session:
        try:
            ClientPrefs[request.user.id, client]
        except ObjectNotFound:
            ClientPrefs(user = User[request.user.id], client_name = client)

    request.client = client

@app.errorhandler(404)
def not_found(error):
    if not request.path.startswith('/rest/'):
        return error

    return request.error_formatter(0, 'Not implemented'), 501

def get_entity(req, cls, param = 'id'):
    eid = req.values.get(param)
    if not eid:
        return False, req.error_formatter(10, 'Missing %s id' % cls.__name__)

    try:
        eid = uuid.UUID(eid)
        entity = cls[eid]
        return True, entity
    except ValueError:
        return False, req.error_formatter(0, 'Invalid %s id' % cls.__name__)
    except ObjectNotFound:
        return False, (req.error_formatter(70, '%s not found' % cls.__name__), 404)

from .system import *
from .browse import *
from .user import *
from .albums_songs import *
from .media import *
from .annotation import *
from .chat import *
from .search import *
from .playlists import *

