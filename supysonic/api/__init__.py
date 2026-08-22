# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

API_VERSION = "1.12.0"

import binascii
import logging

from flask import Blueprint, request
from peewee import IntegrityError

from ..db import ClientPrefs
from ..managers.user import UserManager
from ._exceptions import Unauthorized
from ._formatters import JSONFormatter, JSONPFormatter, XMLFormatter

api = Blueprint("api", __name__)
logger = logging.getLogger(__name__)


def api_routing(endpoint):
    def decorator(func):
        viewendpoint = f"{endpoint}.view"
        api.add_url_rule(endpoint, view_func=func, methods=["GET", "POST"])
        api.add_url_rule(viewendpoint, view_func=func, methods=["GET", "POST"])
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


def decode_password(password):
    if not password.startswith("enc:"):
        return password

    try:
        return binascii.unhexlify(password[4:].encode("utf-8")).decode("utf-8")
    except ValueError:
        return password


@api.before_request
def authorize():
    if request.authorization:
        username = request.authorization.username
        user = UserManager.try_auth(username, request.authorization.password)
        if user is not None:
            request.user = user
            return

        logger.error(
            "Failed login attempt for user %s (IP: %s)", username, request.remote_addr
        )
        raise Unauthorized()

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
def get_client_prefs():
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


from .albums_songs import *
from .annotation import *
from .browse import *
from .chat import *
from .errors import *
from .jukebox import *
from .media import *
from .playlists import *
from .radio import *
from .scan import *
from .search import *
from .system import *
from .unsupported import *
from .user import *
