# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


from flask import current_app
from werkzeug.local import LocalProxy

from .base import SupysonicBaseAppLayer


class SupysonicFlaskAppLayer(SupysonicBaseAppLayer):
    def __init__(self, app):
        super().__init__(app.config)
        app.extensions["supysonic"] = self


def _get_flask_layer():
    return current_app.extensions["supysonic"]


app_layer = LocalProxy(_get_flask_layer)
