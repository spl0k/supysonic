# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import flash, redirect, request, url_for

from ...app.flask import app_layer
from ...frontend._helpers import me_or_uuid
from .. import make_blueprint
from ..exceptions import ScrobblerError

blueprint = make_blueprint("lastfm", __name__)


def _profile(uid):
    return redirect(url_for("frontend.user_profile", uid=uid))


# Intentionally GET: this is the Last.fm OAuth callback. Last.fm redirects the
# user's browser here with a "token" query param, so it must stay GET (making it
# POST-only would return 405 and break account linking).
@blueprint.get("/<uid>/link")
@me_or_uuid
def link(uid, user):
    token = request.args.get("token")
    if not token:
        flash("Missing LastFM auth token", "warning")
        return _profile(uid)

    try:
        app_layer.get_scrobbler("lastfm").link_account(user, token)
    except ScrobblerError as e:
        flash(str(e), "danger")
    else:
        flash("Successfully linked LastFM account", "success")

    return _profile(uid)


@blueprint.post("/<uid>/unlink")
@me_or_uuid
def unlink(uid, user):
    app_layer.get_scrobbler("lastfm").unlink_account(user)
    flash("Unlinked LastFM account", "success")

    return _profile(uid)
