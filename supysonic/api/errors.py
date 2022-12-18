# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import DoesNotExist
from werkzeug.exceptions import BadRequestKeyError

from . import api
from .exceptions import GenericError, MissingParameter, NotFound, ServerError


@api.errorhandler(ValueError)
def value_error(e):
    return GenericError("{0.__class__.__name__}: {0}".format(e))


@api.errorhandler(BadRequestKeyError)
def key_error(e):
    return MissingParameter()


@api.errorhandler(DoesNotExist)
def object_not_found(e):
    return NotFound(e.__class__.__name__[: -len("DoesNotExist")])


@api.errorhandler(500)
def generic_error(e):  # pragma: nocover
    return ServerError("{0.__class__.__name__}: {0}".format(e))


# @api.errorhandler(404)
@api.route("/<path:invalid>", methods=["GET", "POST"])  # blueprint 404 workaround
def not_found(*args, **kwargs):
    return GenericError("Unknown method"), 404
