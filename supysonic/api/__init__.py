# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

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
        user = UserManager.try_auth(request.authorization.username, request.authorization.password)
        if user is not None:
            request.user = user
            return
        raise Unauthorized()

    username = request.values['u']
    password = request.values['p']
    password = decode_password(password)

    user = UserManager.try_auth(username, password)
    if user is None:
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

