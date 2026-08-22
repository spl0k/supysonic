# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from peewee import DoesNotExist
from werkzeug.exceptions import BadRequestKeyError

from . import api
from ._exceptions import GenericError, MissingParameter, NotFound, ServerError

logger = logging.getLogger(__name__)


@api.errorhandler(ValueError)
def value_error(e):
    # Last resort: parameter parsing is supposed to raise InvalidParameter itself, so
    # getting here means either a missed parse site or an actual bug. Either way the
    # details are for us, not for the client.
    logger.exception("Unhandled ValueError", exc_info=e)
    return GenericError("Invalid request")


@api.errorhandler(BadRequestKeyError)
def key_error(e):
    # BadRequestKeyError derives from KeyError, and the mapping raising it passes the
    # missing key as the only argument. str(e) would give the generic HTTP 400
    # description instead of the key name.
    return MissingParameter(e.args[0] if e.args else None)


@api.errorhandler(DoesNotExist)
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
