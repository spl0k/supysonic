# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import (
    Blueprint,
    flash,
    request,
)

from .. import DOWNLOAD_URL, VERSION
from ..app.flask import app_layer
from ..daemon.exceptions import DaemonUnavailableError
from ._helpers import login_check

frontend = Blueprint("frontend", __name__)
frontend.before_request(login_check)


@frontend.context_processor
def inject_metadata():
    return {"version": VERSION, "download_url": DOWNLOAD_URL}


@frontend.before_request
def scan_status():
    if not request.user or not request.user.admin:
        return

    try:
        scanned = app_layer.daemon.get_scanning_progress()
        if scanned is not None:
            flash(f"Scanning in progress, {scanned} files scanned.")
    except DaemonUnavailableError:
        # The daemon is optional. Without one there is no scan to report on, and
        # this is only a status banner, so there's nothing to recover.
        pass
