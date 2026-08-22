# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import binascii
import uuid
from functools import wraps

from flask import request

from ..db import Folder, Track
from ..parsers import parse_bool, parse_float, parse_int, parse_mail
from ._exceptions import (
    Forbidden,
    GenericError,
    InvalidParameter,
    MissingParameter,
    NotFound,
)

#: Upper bound for the various 'size'/'count' paging parameters. Matches the value
#: documented by Subsonic for getRandomSongs and getAlbumList.
MAX_LIST_SIZE = 500

#: Upper bound for the millisecond timestamps some endpoints take. Anything above
#: this is out of datetime's range and would end up as an unhandled OverflowError
#: rather than a proper API error. Year 3000 is well past any legitimate value.
MAX_TIMESTAMP_MS = 32503680000000


def admin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.user.admin:
            raise Forbidden()
        return f(*args, **kwargs)

    return decorated


def decode_password(password):
    if not password.startswith("enc:"):
        return password

    try:
        return binascii.unhexlify(password[4:].encode("utf-8")).decode("utf-8")
    except ValueError:
        return password


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


def get_mail(param, default=None, required=False):
    """Read an email address request parameter.

    Raises MissingParameter if it is absent and required, InvalidParameter if its
    value doesn't look like an email address.
    """

    try:
        value = parse_mail(request.values.get(param))
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
