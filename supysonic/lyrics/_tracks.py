# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Library lookup shared by the providers reading lyrics off the track files."""

from ..db.models import Artist, Track

# Upper bound on how many candidate tracks are opened looking for lyrics — a
# loose artist/title match can otherwise touch the whole library.
MAX_CANDIDATES = 10


def candidate_tracks(artist, title):
    """The tracks of the library loosely matching ``artist`` and ``title``."""

    return (
        Track.select()
        .join(Artist)
        .where(Track.title.contains(title), Artist.name.contains(artist))
        .order_by(Track.title, Track.id)
        .limit(MAX_CANDIDATES)
    )
