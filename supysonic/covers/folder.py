# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path

from ..db.models import Album, Folder, Track
from . import Cover, CoverArtProvider


class FolderCoverArtProvider(CoverArtProvider):
    """Image files lying next to the tracks, as picked by the scanner.

    The cover belongs to the folder holding it. Tracks of that folder fall back
    on it, as do albums having tracks there.
    """

    name = "folder"
    configured = True

    def __init__(self, config):
        pass

    def find_covers(self, entities):
        if not entities:
            return {}

        if isinstance(entities[0], Folder):
            return {f.id: f.id for f in entities if f.cover_art}

        if isinstance(entities[0], Track):
            return {t.id: t.folder.id for t in entities if t.folder.cover_art}

        if isinstance(entities[0], Album):
            covers = {}
            for aid, fid in (
                Track.select(Track.album, Folder.id)
                .join(Folder, on=Track.folder)
                .where(
                    Track.album.in_([a.id for a in entities]),
                    Folder.cover_art.is_null(False),
                )
                .tuples()
            ):
                covers.setdefault(aid, fid)
            return covers

        return {}

    def get_cover(self, entity):
        if not isinstance(entity, Folder) or not entity.cover_art:
            return None

        # The scanner might not have caught up with a removal yet
        path = os.path.join(entity.path, entity.cover_art)
        if not os.path.isfile(path):
            return None

        return Cover(path=path)


PROVIDER = FolderCoverArtProvider
