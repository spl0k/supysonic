# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import current_app, request
from werkzeug.exceptions import HTTPException


class SubsonicAPIException(HTTPException):
    code = 400
    api_code = None
    message = None

    def get_response(self, environ=None):
        rv = request.formatter.error(self.api_code, self.message)
        # rv.status_code = self.code
        return rv

    def __str__(self):
        code = self.api_code if self.api_code is not None else "??"
        return f"{code}: {self.message}"


class GenericError(SubsonicAPIException):
    api_code = 0

    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


class ServerError(GenericError):
    code = 500


class UnsupportedParameter(GenericError):
    def __init__(self, parameter, *args, **kwargs):
        message = f"Unsupported parameter '{parameter}'"
        super().__init__(message, *args, **kwargs)


class MissingParameter(SubsonicAPIException):
    api_code = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = "A required parameter is missing."


class ClientMustUpgrade(SubsonicAPIException):
    api_code = 20
    message = "Incompatible Subsonic REST protocol version. Client must upgrade."


class ServerMustUpgrade(SubsonicAPIException):
    code = 501
    api_code = 30
    message = "Incompatible Subsonic REST protocol version. Server must upgrade."


class Unauthorized(SubsonicAPIException):
    code = 401
    api_code = 40
    message = "Wrong username or password."


class Forbidden(SubsonicAPIException):
    code = 403
    api_code = 50
    message = "User is not authorized for the given operation."


class TrialExpired(SubsonicAPIException):
    code = 402
    api_code = 60
    message = (
        "The trial period for the Supysonic server is over."
        "But since it doesn't use any licensing you shouldn't be seeing this error ever."
        "So something went wrong or you got scammed."
    )


class NotFound(SubsonicAPIException):
    code = 404
    api_code = 70

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = f"{entity} not found"


class AggregateException(SubsonicAPIException):
    def __init__(self, exceptions, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.exceptions = []
        for exc in exceptions:
            if not isinstance(exc, SubsonicAPIException):
                # Try to convert regular exceptions to SubsonicAPIExceptions
                handler = current_app._find_error_handler(exc)  # meh
                if handler:
                    exc = handler(exc)
                    assert isinstance(exc, SubsonicAPIException)
                else:
                    exc = GenericError(str(exc))
            self.exceptions.append(exc)

    def get_response(self, environ=None):
        if len(self.exceptions) == 1:
            return self.exceptions[0].get_response()

        codes = {exc.api_code for exc in self.exceptions}
        errors = [
            {"code": exc.api_code, "message": exc.message} for exc in self.exceptions
        ]

        rv = request.formatter(
            "error",
            {"code": next(iter(codes)) if len(codes) == 1 else 0, "error": errors},
        )
        # rv.status_code = self.code
        return rv
