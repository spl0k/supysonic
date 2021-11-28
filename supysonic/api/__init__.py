# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

API_VERSION = "1.10.2"

import binascii
import uuid
from flask import request
from flask import Blueprint
from pony.orm import ObjectNotFound, TransactionIntegrityError
from pony.orm import commit

from ..db import ClientPrefs, Folder
from ..managers.user import UserManager

from .exceptions import GenericError, Unauthorized
from .formatters import JSONFormatter, JSONPFormatter, XMLFormatter

api = Blueprint("api", __name__)


def api_routing(endpoint):
    def decorator(func):
        viewendpoint = "{}.view".format(endpoint)
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
        user = UserManager.try_auth(
            request.authorization.username, request.authorization.password
        )
        if user is not None:
            request.user = user
            return
        raise Unauthorized()

    username = request.values["u"]
    password = request.values["p"]
    password = decode_password(password)

    user = UserManager.try_auth(username, password)
    if user is None:
        raise Unauthorized()

    request.user = user


@api.before_request
def get_client_prefs():
    client = request.values["c"]
    try:
        request.client = ClientPrefs[request.user, client]
    except ObjectNotFound:
        try:
            request.client = ClientPrefs(user=request.user, client_name=client)
            commit()
        except TransactionIntegrityError:
            # We might have hit a race condition here, another request already created
            # the ClientPrefs. Issue #220
            # Reload the user or Pony will complain about different transactions
            request.user = UserManager.get(request.user.id)
            request.client = ClientPrefs[request.user, client]


def get_entity(cls, param="id"):
    eid = request.values[param]
    if cls == Folder:
        eid = int(eid)
    else:
        eid = uuid.UUID(eid)
    entity = cls[eid]
    return entity


def get_entity_id(cls, eid):
    """Return the entity ID as its proper type."""
    if cls == Folder:
        if isinstance(eid, uuid.UUID):
            raise GenericError("Invalid ID")
        try:
            return int(eid)
        except ValueError:
            raise GenericError("Invalid ID")
    try:
        return uuid.UUID(eid)
    except (AttributeError, ValueError):
        raise GenericError("Invalid ID")


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
from .jukebox import *
from .radio import *
from .unsupported import *
from .scan import *
