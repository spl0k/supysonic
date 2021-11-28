# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#               2020 Vincent Ducamps
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request
from flask import current_app

from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError

from . import api_routing
from .user import admin_only
from .exceptions import ServerError


@api_routing("/startScan")
@admin_only
def startScan():
    try:
        daemonclient = DaemonClient(current_app.config["DAEMON"]["socket"])
        daemonclient.scan()
        scanned = daemonclient.get_scanning_progress()
    except DaemonUnavailableError as e:
        raise ServerError(str(e))
    return request.formatter(
        "scanStatus",
        {
            "scanning": scanned is not None,
            "count": scanned or 0,
        },
    )


@api_routing("/getScanStatus")
@admin_only
def getScanStatus():
    try:
        scanned = DaemonClient(
            current_app.config["DAEMON"]["socket"]
        ).get_scanning_progress()
    except DaemonUnavailableError as e:
        raise ServerError(str(e))
    return request.formatter(
        "scanStatus",
        {
            "scanning": scanned is not None,
            "count": scanned or 0,
        },
    )
