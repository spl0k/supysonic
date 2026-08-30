# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import render_template

from ..db import Album, Artist, Track
from ._blueprint import frontend


@frontend.get("/")
def index():
    stats = {
        "artists": Artist.select().count(),
        "albums": Album.select().count(),
        "tracks": Track.select().count(),
    }
    return render_template("home.html", stats=stats)
