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

from flask import request,Response
import simplejson
import uuid

from dict2xml import *

from web import app
from managers.user import UserManager


# To encode the custom UUID type from database
class SupysonicEncoder(simplejson.JSONEncoder):
    def default(self, o):
        return unicode(o)

@app.before_request
def set_formatter():
    if not request.path.startswith('/rest/'):
        return

    """Return a function to create the response."""
    (f, callback) = map(request.args.get, ['f', 'callback'])
    if f == 'jsonp':
        # Some clients (MiniSub, Perisonic) set f to jsonp without callback for streamed data
        if not callback and request.endpoint not in [ 'stream_media', 'cover_art' ]:
            return ResponseHelper.responsize_json({
                'error': {
                    'code': 0,
                    'message': 'Missing callback'
                }
            }, error = True), 400
        request.formatter = lambda x, **kwargs: ResponseHelper.responsize_jsonp(x, callback, kwargs)
    elif f == "json":
        request.formatter = ResponseHelper.responsize_json
    else:
        request.formatter = ResponseHelper.responsize_xml

    request.error_formatter = lambda code, msg: request.formatter({ 'error': { 'code': code, 'message': msg } }, error = True)

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

    (username, password) = map(request.args.get, [ 'u', 'p' ])
    if not username or not password:
        return error

    status, user = UserManager.try_auth(username, password)
    if status != UserManager.SUCCESS:
        return error

    request.username = username
    request.user = user

@app.after_request
def set_content_type(response):
    if not request.path.startswith('/rest/'):
        return response

    if response.mimetype.startswith('text'):
        f = request.args.get('f')
        response.headers['content-type'] = 'application/json' if f in [ 'jsonp', 'json' ] else 'text/xml'

    return response

@app.errorhandler(404)
def not_found(error):
    if not request.path.startswith('/rest/'):
        return error

    return request.error_formatter(0, 'Not implemented'), 501

class ResponseHelper:

    @staticmethod
    def responsize_json(ret, error = False, version = "1.8.0"):
        def check_lists(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    d[key] = check_lists(value)
                elif isinstance(value, list):
                    if len(value) == 0:
                        del d[key]
                    else:
                        d[key] = [ check_lists(item) if isinstance(item, dict) else item for item in value ]
            return d

        ret = check_lists(ret)
        # add headers to response
        ret.update({
            'status': 'failed' if error else 'ok',
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })
        return simplejson.dumps({ 'subsonic-response': ret }, indent = True, encoding = 'utf-8', cls=SupysonicEncoder)


    @staticmethod
    def responsize_jsonp(ret, callback, error = False, version = "1.8.0"):
        return "%s(%s)" % (callback, ResponseHelper.responsize_json(ret, error, version))


    @staticmethod
    def responsize_xml(ret, error = False, version = "1.8.0"):
        ret.update({
            'status': 'failed' if error else 'ok',
            'version': version,
            'xmlns': "http://subsonic.org/restapi"
        })

        output = dict2xml(ret, "subsonic-response")

        return Response(u'<?xml version="1.0" encoding="UTF-8"?>' + output, content_type='text/xml; charset=utf-8')




def get_entity(req, ent, param = 'id'):
    eid = req.args.get(param)
    if not eid:
        return False, req.error_formatter(10, 'Missing %s id' % ent.__name__)

    try:
        eid = uuid.UUID(eid)
    except:
        return False, req.error_formatter(0, 'Invalid %s id' % ent.__name__)

    entity = session.query(ent).get(eid)
    if not entity:
        return False, (req.error_formatter(70, '%s not found' % ent.__name__), 404)

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

