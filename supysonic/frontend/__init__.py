# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import (
    current_app,
    flash,
    redirect,
    request,
    render_template,
    session,
    url_for,
)
from flask import Blueprint
from functools import wraps

from .. import VERSION, DOWNLOAD_URL
from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Artist, Album, Track
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
        return redirect(
            url_for(
                "frontend.login",
                returnUrl=request.script_root
                + request.url[len(request.url_root) - 1 :],
            )
        )


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
        pass


@frontend.route("/")
def index():
    stats = {
        "artists": Artist.select().count(),
        "albums": Album.select().count(),
        "tracks": Track.select().count(),
    }
    return render_template("home.html", stats=stats)


def admin_only(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not request.user or not request.user.admin:
            return redirect(url_for("frontend.index"))
        return f(*args, **kwargs)

    return decorated_func


from .user import *
from .folder import *
from .playlist import *
