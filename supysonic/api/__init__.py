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
from pony.orm import ObjectNotFound

from ..managers.user import UserManager
from ..py23 import dict

from .exceptions import Unauthorized
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
    if request.authorization:
        status, user = UserManager.try_auth(request.authorization.username, request.authorization.password)
        if status == UserManager.SUCCESS:
            request.user = user
            return
        raise Unauthorized()

    username = request.values['u']
    password = request.values['p']
    password = decode_password(password)

    status, user = UserManager.try_auth(username, password)
    if status != UserManager.SUCCESS:
        raise Unauthorized()

    request.user = user

@api.before_request
def get_client_prefs():
    client = request.values['c']
    try:
        ClientPrefs[request.user, client]
    except ObjectNotFound:
        ClientPrefs(user = request.user, client_name = client)

    request.client = client

def get_entity(cls, param = 'id'):
    eid = request.values[param]
    eid = uuid.UUID(eid)
    entity = cls[eid]
    return entity

from .errors import *

from .system import *
from .browse import *
from .user import *
from .albums_songs import *
from .media import *
from .annotation import *
from .chat import *
from .search import *
from .playlists import *

