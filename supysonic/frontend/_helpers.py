# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from functools import wraps

from flask import redirect, request, url_for

from ..parsers import FALSE_VALUES


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
