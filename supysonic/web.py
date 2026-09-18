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
from .config import Config
from .frontend import get_frontend_blueprint
from .logs import setup_logging


def create_application(config=None, testing=False):
    # Flask!
    app = Flask(__name__)

    # Flask's own settings. The Supysonic config is a separate object, reachable
    # through the app layer, and deliberately not merged into app.config
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    if testing:
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    if not config:  # pragma: nocover
        config = Config.from_common_locations()

    setup_logging(config.webapp)

    # Insert unknown mimetypes
    for k, v in config.mimetypes.items():
        extension = "." + k.lower()
        if extension not in mimetypes.types_map:
            mimetypes.add_type(v, extension, False)

    SupysonicFlaskAppLayer.register_on(app, config)

    csrf = CSRFProtect()
    csrf.init_app(app)

    # Mount app sections
    if config.webapp.mount_webui:
        app.register_blueprint(get_frontend_blueprint())
    if config.webapp.mount_api:
        api = get_api_blueprint()
        app.register_blueprint(api, url_prefix="/rest")
        # The Subsonic API has its own auth and is used by non-browser clients
        # that don't send CSRF tokens; exempt it from CSRF protection.
        csrf.exempt(api)

    return app
