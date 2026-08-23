# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from .. import DOWNLOAD_URL, VERSION
from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import User
from ..managers.user import UserManager

frontend = Blueprint("frontend", __name__)


@frontend.context_processor
def inject_metadata():
    return {"version": VERSION, "download_url": DOWNLOAD_URL}


@frontend.before_request
def login_check():
    request.user = None
    should_login = True
    if session.get("userid"):
        try:
            user = UserManager.get(session.get("userid"))
            request.user = user
            should_login = False
        except (ValueError, User.DoesNotExist):
            session.clear()

    if should_login and request.endpoint != "frontend.login":
        flash("Please login")
        return redirect(url_for("frontend.login"))


@frontend.before_request
def scan_status():
    if not request.user or not request.user.admin:
        return

    try:
        scanned = DaemonClient(
            current_app.config["DAEMON"]["socket"]
        ).get_scanning_progress()
        if scanned is not None:
            flash(f"Scanning in progress, {scanned} files scanned.")
    except DaemonUnavailableError:
        # The daemon is optional. Without one there is no scan to report on, and
        # this is only a status banner, so there's nothing to recover.
        pass
