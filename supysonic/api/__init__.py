# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

API_VERSION = "1.12.0"

import binascii
import logging
import uuid

from flask import Blueprint, request
from peewee import IntegrityError

from ..db import ClientPrefs, Folder, Track
from ..managers.user import UserManager
from ..utils import parse_bool, parse_float, parse_int
from .exceptions import (
    GenericError,
    InvalidParameter,
    MissingParameter,
    NotFound,
    Unauthorized,
)
from .formatters import JSONFormatter, JSONPFormatter, XMLFormatter

api = Blueprint("api", __name__)
logger = logging.getLogger(__name__)

#: Upper bound for the various 'size'/'count' paging parameters. Matches the value
#: documented by Subsonic for getRandomSongs and getAlbumList.
MAX_LIST_SIZE = 500

#: Upper bound for the millisecond timestamps some endpoints take. Anything above
#: this is out of datetime's range and would end up as an unhandled OverflowError
#: rather than a proper API error. Year 3000 is well past any legitimate value.
MAX_TIMESTAMP_MS = 32503680000000


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


def get_bool(param, default=None, required=False):
    """Read a boolean request parameter.

    Raises MissingParameter if it is absent and required, InvalidParameter if its
    value isn't a recognized boolean.
    """

    try:
        value = parse_bool(request.values.get(param))
    except ValueError as e:
        raise InvalidParameter(param) from e

    if value is None:
        if required:
            raise MissingParameter(param)
        return default
    return value


def get_int(param, default=None, min=None, max=None, required=False):
    """Read an integer request parameter, enforcing optional bounds.

    Raises MissingParameter if it is absent and required, InvalidParameter if its
    value isn't a valid integer or is out of bounds.
    """

    try:
        value = parse_int(request.values.get(param), min, max)
    except ValueError as e:
        raise InvalidParameter(param, e) from e

    if value is None:
        if required:
            raise MissingParameter(param)
        return default
    return value


def get_float(param, default=None, min=None, max=None, required=False):
    """Same as get_int, for floats."""

    try:
        value = parse_float(request.values.get(param), min, max)
    except ValueError as e:
        raise InvalidParameter(param, e) from e

    if value is None:
        if required:
            raise MissingParameter(param)
        return default
    return value


def get_entity(cls, param="id"):
    return cls[get_entity_id(cls, request.values[param])]


def get_entity_id(cls, eid):
    """Return the entity ID as its proper type."""
    if cls == Folder:
        if isinstance(eid, uuid.UUID):
            raise GenericError("Invalid ID")
        try:
            return int(eid)
        except ValueError as e:
            raise GenericError("Invalid ID") from e
    try:
        return uuid.UUID(eid)
    except (AttributeError, ValueError) as e:
        raise GenericError("Invalid ID") from e


def resolve_child_id(eid):
    """Resolve an ambiguous child ID to the class it belongs to.

    Folder IDs are ints while Track and Album IDs are UUIDs, so the ID itself
    tells which kind it is. Returns a (class, id) pair, the class being either
    Folder or Track. Raises GenericError if the ID is neither.
    """

    try:
        return Folder, get_entity_id(Folder, eid)
    except GenericError:
        # Not an int, so it can only be a UUID
        return Track, get_entity_id(Track, eid)


def get_root_folder(id):
    if id is None:
        return None

    try:
        fid = int(id)
    except ValueError as e:
        raise InvalidParameter("musicFolderId") from e

    try:
        return Folder.get(id=fid, root=True)
    except Folder.DoesNotExist as e:
        raise NotFound("Folder") from e


def get_music_folder():
    """Return the root Folder given by the 'musicFolderId' parameter, if any."""
    return get_root_folder(request.values.get("musicFolderId"))


def get_paging(count_param, offset_param="offset", default=20):
    """Read a (count, offset) pair of paging parameters."""

    return (
        get_int(count_param, default, min=0, max=MAX_LIST_SIZE),
        get_int(offset_param, 0, min=0),
    )


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
