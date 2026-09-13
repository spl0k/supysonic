# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import mimetypes

from flask import Flask
from flask_wtf import CSRFProtect

from .api import get_api_blueprint
from .app.flask import SupysonicFlaskAppLayer
from .config import IniConfig
from .frontend import get_frontend_blueprint
from .logs import setup_logging


def create_application(config=None):
    # Flask!
    app = Flask(__name__)
    app.config.from_object("supysonic.config.DefaultConfig")

    if not config:  # pragma: nocover
        config = IniConfig.from_common_locations()
    app.config.from_object(config)

    setup_logging(app.config["WEBAPP"])

    # Insert unknown mimetypes
    for k, v in app.config["MIMETYPES"].items():
        extension = "." + k.lower()
        if extension not in mimetypes.types_map:
            mimetypes.add_type(v, extension, False)

    SupysonicFlaskAppLayer.register_on(app)

    csrf = CSRFProtect()
    csrf.init_app(app)

    # Mount app sections
    if app.config["WEBAPP"]["mount_webui"]:
        app.register_blueprint(get_frontend_blueprint())
    if app.config["WEBAPP"]["mount_api"]:
        api = get_api_blueprint()
        app.register_blueprint(api, url_prefix="/rest")
        # The Subsonic API has its own auth and is used by non-browser clients
        # that don't send CSRF tokens; exempt it from CSRF protection.
        csrf.exempt(api)

    return app
