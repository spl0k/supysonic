# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request
from werkzeug.exceptions import HTTPException

class SubsonicAPIError(HTTPException):
    code = 400
    api_code = None
    message = None

    def get_response(self, environ = None):
        rv = request.formatter.error(self.api_code, self.message)
        rv.status_code = self.code
        return rv

    def __str__(self):
        code = self.api_code if self.api_code is not None else '??'
        return '{}: {}'.format(code, self.message)

class GenericError(SubsonicAPIError):
    api_code = 0

    def __init__(self, message, *args, **kwargs):
        super(GenericError, self).__init__(*args, **kwargs)
        self.message = message

class ServerError(GenericError):
    code = 500

class MissingParameter(SubsonicAPIError):
    api_code = 10

    def __init__(self, param, *args, **kwargs):
        super(MissingParameter, self).__init__(*args, **kwargs)
        self.message = "Required parameter '{}' is missing.".format(param)

class ClientMustUpgrade(SubsonicAPIError):
    api_code = 20
    message = 'Incompatible Subsonic REST protocol version. Client must upgrade.'

class ServerMustUpgrade(SubsonicAPIError):
    code = 501
    api_code = 30
    message = 'Incompatible Subsonic REST protocol version. Server must upgrade.'

class Unauthorized(SubsonicAPIError):
    code = 401
    api_code = 40
    message = 'Wrong username or password.'

class Forbidden(SubsonicAPIError):
    code = 403
    api_code = 50
    message = 'User is not authorized for the given operation.'

class TrialExpired(SubsonicAPIError):
    code = 402
    api_code = 60
    message = ("The trial period for the Supysonic server is over."
        "But since it doesn't use any licensing you shouldn't be seeing this error ever."
        "So something went wrong or you got scammed.")

class NotFound(SubsonicAPIError):
    code = 404
    api_code = 70

    def __init__(self, entity, *args, **kwargs):
        super(NotFound, self).__init__(*args, **kwargs)
        self.message = '{} not found'.format(entity)

