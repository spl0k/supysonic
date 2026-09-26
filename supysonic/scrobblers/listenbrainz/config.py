# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from ...config import Option, Section


class ListenBrainzSection(Section, section="listenbrainz"):
    api_url = Option("https://api.listenbrainz.org")
