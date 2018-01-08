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

import binascii
import simplejson
import uuid

from flask import request, current_app as app
from pony.orm import db_session, ObjectNotFound
from xml.dom import minidom
from xml.etree import ElementTree

from ..managers.user import UserManager
from ..py23 import strtype

from builtins import dict

@app.before_request
def set_formatter():
    if not request.path.startswith('/rest/'):
        return

    """Return a function to create the response."""
    (f, callback) = map(request.values.get, ['f', 'callback'])
    if f == 'jsonp':
        # Some clients (MiniSub, Perisonic) set f to jsonp without callback for streamed data
        if not callback and request.endpoint not in [ 'stream_media', 'cover_art' ]:
            return ResponseHelper.responsize_json(dict(
                error = dict(
                    code = 10,
                    message = 'Missing callback'
                )
            ), error = True), 400
        request.formatter = lambda x, **kwargs: ResponseHelper.responsize_jsonp(x, callback, kwargs)
    elif f == "json":
        request.formatter = ResponseHelper.responsize_json
    else:
        request.formatter = ResponseHelper.responsize_xml

    request.error_formatter = lambda code, msg: request.formatter(dict(error = dict(code = code, message = msg)), error = True)

def decode_password(password):
    if not password.startswith('enc:'):
        return password

    try:
        return binascii.unhexlify(password[4:]).decode('utf-8')
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

@app.after_request
def set_headers(response):
    if not request.path.startswith('/rest/'):
        return response

    if response.mimetype.startswith('text'):
        f = request.values.get('f')
        # TODO set the mimetype when creating the response, here we could lose some info
        if f == 'json':
            response.headers['Content-Type'] = 'application/json'
        elif f == 'jsonp':
            response.headers['Content-Type'] = 'application/javascript'
        else:
            response.headers['Content-Type'] = 'text/xml'

    response.headers['Access-Control-Allow-Origin'] = '*'

    return response

@app.errorhandler(404)
def not_found(error):
    if not request.path.startswith('/rest/'):
        return error

    return request.error_formatter(0, 'Not implemented'), 501

class ResponseHelper:

    @staticmethod
    def remove_empty_lists(d):
        if not isinstance(d, dict):
            raise TypeError('Expecting a dict')

        for key, value in d.items():
            if isinstance(value, dict):
                d[key] = ResponseHelper.remove_empty_lists(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    del d[key]
                else:
                    d[key] = [ ResponseHelper.remove_empty_lists(item) if isinstance(item, dict) else item for item in value ]
        return d

    @staticmethod
    def responsize_json(ret, error = False, version = "1.8.0"):
        ret = ResponseHelper.remove_empty_lists(ret)

        # add headers to response
        ret.update(
            status = 'failed' if error else 'ok',
            version = version
        )
        return simplejson.dumps({ 'subsonic-response': ret }, indent = True, encoding = 'utf-8')

    @staticmethod
    def responsize_jsonp(ret, callback, error = False, version = "1.8.0"):
        return "%s(%s)" % (callback, ResponseHelper.responsize_json(ret, error, version))

    @staticmethod
    def responsize_xml(ret, error = False, version = "1.8.0"):
        """Return an xml response from json and replace unsupported characters."""
        ret.update(
            status = 'failed' if error else 'ok',
            version = version,
            xmlns = "http://subsonic.org/restapi"
        )

        elem = ElementTree.Element('subsonic-response')
        ResponseHelper.dict2xml(elem, ret)

        return minidom.parseString(ElementTree.tostring(elem)).toprettyxml(indent = '  ', encoding = 'UTF-8')

    @staticmethod
    def dict2xml(elem, dictionary):
        """Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.
          ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
            ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
            ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
            ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }
            ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
            "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}
                """
        if not isinstance(dictionary, dict):
            raise TypeError('Expecting a dict')
        if not all(map(lambda x: isinstance(x, strtype), dictionary)):
            raise TypeError('Dictionary keys must be strings')

        for name, value in dictionary.items():
            if name == '_value_':
                elem.text = ResponseHelper.value_tostring(value)
            elif isinstance(value, dict):
                subelem = ElementTree.SubElement(elem, name)
                ResponseHelper.dict2xml(subelem, value)
            elif isinstance(value, list):
                for v in value:
                    subelem = ElementTree.SubElement(elem, name)
                    if isinstance(v, dict):
                        ResponseHelper.dict2xml(subelem, v)
                    else:
                        subelem.text = ResponseHelper.value_tostring(v)
            else:
                elem.set(name, ResponseHelper.value_tostring(value))

    @staticmethod
    def value_tostring(value):
        if value is None:
            return None
        if isinstance(value, strtype):
            return value
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

def get_entity(req, cls, param = 'id'):
    eid = req.values.get(param)
    if not eid:
        return False, req.error_formatter(10, 'Missing %s id' % cls.__name__)

    try:
        eid = uuid.UUID(eid)
    except:
        return False, req.error_formatter(0, 'Invalid %s id' % cls.__name__)

    try:
        entity = cls[eid]
    except ObjectNotFound:
        return False, (req.error_formatter(70, '%s not found' % cls.__name__), 404)

    return True, entity

from .system import *
from .browse import *
from .user import *
from .albums_songs import *
from .media import *
from .annotation import *
from .chat import *
from .search import *
from .playlists import *

