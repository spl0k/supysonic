# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

import mediafile

from ..db.models import Album, Folder, Track
from . import Cover, CoverArtProvider

logger = logging.getLogger(__name__)


class EmbeddedCoverArtProvider(CoverArtProvider):
    """Images embedded in the tags of the tracks.

    The cover belongs to the track carrying it. Folders and albums fall back on
    the cover of one of their tracks.
    """

    name = "embedded"
    configured = True

    def __init__(self, config):
        pass

    def find_covers(self, entities):
        if not entities:
            return {}

        if isinstance(entities[0], Track):
            return {t.id: t.id for t in entities if t.has_art}

        if isinstance(entities[0], Folder):
            field = Track.folder
        elif isinstance(entities[0], Album):
            field = Track.album
        else:
            return {}

        covers = {}
        for eid, tid in (
            Track.select(field, Track.id)
            .where(field.in_([e.id for e in entities]), Track.has_art)
            .tuples()
        ):
            covers.setdefault(eid, tid)
        return covers

    def get_cover(self, entity):
        if not isinstance(entity, Track):
            return None

        try:
            art = mediafile.MediaFile(entity.path).art
        except mediafile.UnreadableFileError as e:
            logger.warning("Can't read tags of %s: %s", entity.path, e)
            return None

        if not art:
            return None

        return Cover(data=art)


PROVIDER = EmbeddedCoverArtProvider
