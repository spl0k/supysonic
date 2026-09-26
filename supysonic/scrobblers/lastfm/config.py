# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from ...config import Option, Section


class LastFmSection(Section, section="lastfm"):
    api_url = Option("https://ws.audioscrobbler.com/2.0/")
    api_key = Option()
    secret = Option()
