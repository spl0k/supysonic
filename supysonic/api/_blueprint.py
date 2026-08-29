# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from flask import Blueprint, request
from peewee import DoesNotExist, IntegrityError
from werkzeug.exceptions import BadRequestKeyError

from ..db import ClientPrefs
from ..managers.user import UserManager
from ._exceptions import (
    GenericError,
    MissingParameter,
    NotFound,
    ServerError,
    Unauthorized,
    register_converter,
)
from ._formatters import JSONFormatter, JSONPFormatter, XMLFormatter
from ._helpers import decode_password

api = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


def api_routing(endpoint):
    def decorator(func):
        viewendpoint = f"{endpoint}.view"
        api.add_url_rule(endpoint, view_func=func, methods=["GET", "POST"])
        api.add_url_rule(viewendpoint, view_func=func, methods=["GET", "POST"])
        return func

    return decorator


def api_errorhandler(exc_type):
    """Register func as the handler for exc_type, both for Flask's own dispatch and for
    the conversion done when exceptions are collected into an AggregateException.

    Only takes exception classes. For HTTP status codes use api.errorhandler directly.
    """

    def decorator(func):
        api.errorhandler(exc_type)(func)
        register_converter(exc_type, func)
        return func

    return decorator


@api.before_request
def set_formatter():
    """Return a function to create the response."""
    f, callback = map(request.values.get, ("f", "callback"))
    if f == "jsonp":
        request.formatter = JSONPFormatter(callback)
    elif f == "json":
        request.formatter = JSONFormatter()
    else:
        request.formatter = XMLFormatter()


@api.before_request
def authorize():
    username = None
    password = None

    if request.authorization:
        username = request.authorization.username
        password = request.authorization.password
    else:
        username = request.values["u"]
        password = request.values["p"]
        password = decode_password(password)

    user = UserManager.try_auth(username, password)
    if user is None:
        logger.error(
            "Failed login attempt for user %s (IP: %s)", username, request.remote_addr
        )
        raise Unauthorized()

    request.user = user


@api.before_request
def set_client_prefs():
    client = request.values["c"]
    try:
        request.client = ClientPrefs[request.user, client]
    except ClientPrefs.DoesNotExist:
        try:
            request.client = ClientPrefs.create(user=request.user, client_name=client)
        except IntegrityError:
            # We might have hit a race condition here, another request already created
            # the ClientPrefs. Issue #220
            request.client = ClientPrefs[request.user, client]


@api_errorhandler(ValueError)
def value_error(e):
    # Last resort: parameter parsing is supposed to raise InvalidParameter itself, so
    # getting here means either a missed parse site or an actual bug. Either way the
    # details are for us, not for the client.
    logger.exception("Unhandled ValueError", exc_info=e)
    return GenericError("Invalid request")


@api_errorhandler(BadRequestKeyError)
def key_error(e):
    # BadRequestKeyError derives from KeyError, and the mapping raising it passes the
    # missing key as the only argument. str(e) would give the generic HTTP 400
    # description instead of the key name.
    return MissingParameter(e.args[0] if e.args else None)


@api_errorhandler(DoesNotExist)
def object_not_found(e):
    # Deliberately generic: the model raising this can be an implementation detail
    # (PlaylistTrack, ClientPrefs, ...) that clients have no business knowing about.
    # Endpoints naming a public entity raise NotFound themselves.
    logger.debug("Not found: %s", e.__class__.__name__)
    return NotFound("The requested data")


@api.errorhandler(500)
def generic_error(e):  # pragma: nocover
    logger.exception("Unhandled exception", exc_info=e)
    return ServerError("Server error")


# @api.errorhandler(404)
@api.route("/<path:invalid>", methods=["GET", "POST"])  # blueprint 404 workaround
def not_found(*args, **kwargs):
    return GenericError("Unknown method"), 404
