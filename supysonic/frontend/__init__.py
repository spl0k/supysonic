# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import pkgutil
from functools import cache
from importlib import import_module


@cache
def get_frontend_blueprint():
    from ._blueprint import frontend

    for name in sorted(m.name for m in pkgutil.iter_modules(__path__)):
        if not name.startswith("_"):
            import_module(f".{name}", __package__)

    return frontend
