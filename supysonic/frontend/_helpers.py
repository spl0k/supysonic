# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from functools import wraps

from flask import flash, redirect, request, session, url_for

from ..app.flask import app_layer
from ..db.models import User
from ..parsers import FALSE_VALUES


def login_check():
    request.user = None
    should_login = True
    if session.get("userid"):
        try:
            user = app_layer.users.get(session.get("userid"))
            request.user = user
            should_login = False
        except (ValueError, User.DoesNotExist):
            session.clear()

    if should_login and request.endpoint != "frontend.login":
        flash("Please login")
        return redirect(url_for("frontend.login"))


def parse_checkbox(form, name):
    """Read an HTML checkbox out of a submitted form.

    Browsers omit unchecked boxes entirely and send 'on' when checked, so presence
    means true. Explicit negatives are still honoured for hand-crafted requests and
    for the few templates that submit a hidden value.
    """

    value = form.get(name)
    if value is None:
        return False
    return value.strip().lower() not in ("", *FALSE_VALUES)


def admin_only(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not request.user or not request.user.admin:
            return redirect(url_for("frontend.index"))
        return f(*args, **kwargs)

    return decorated_func


def _resolve_user(uid):
    """Look up the user with the given id.

    Returns a (user, response) tuple. On failure the user is None and the
    response is a redirection to the index, the error having been flashed.
    """

    try:
        return app_layer.users.get(uid), None
    except ValueError as e:
        flash(str(e), "danger")
    except User.DoesNotExist:
        flash("No such user", "danger")

    return None, redirect(url_for("frontend.index"))


def _resolve_me_or_uuid(uid):
    """Same as _resolve_user, but 'me' resolves to the requesting user.

    Any other id is reserved to admins.
    """

    if uid == "me":
        return request.user, None
    if not request.user.admin:
        return None, redirect(url_for("frontend.index"))

    return _resolve_user(uid)


def _user_injector(resolve, arg="uid"):
    """Build a decorator passing the user resolved from a view's uid to it."""

    def decorator(f):
        @wraps(f)
        def decorated_func(*args, **kwargs):
            if kwargs:
                uid = kwargs[arg]
            else:
                uid = args[0]

            user, error = resolve(uid)
            if error is not None:
                return error

            if kwargs:
                kwargs["user"] = user
            else:
                args = (uid, user)

            return f(*args, **kwargs)

        return decorated_func

    return decorator


me_or_uuid = _user_injector(_resolve_me_or_uuid)
uuid_user = _user_injector(_resolve_user)
