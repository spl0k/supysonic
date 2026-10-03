# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Lyrics stored in the tags of the track files."""

import logging

import mediafile

from . import Lyrics, LyricsProvider
from ._tracks import candidate_tracks

logger = logging.getLogger(__name__)


class EmbeddedLyricsProvider(LyricsProvider):
    name = "embedded"
    configured = True

    def __init__(self, config):
        pass

    def get_lyrics(self, artist, title):
        for track in candidate_tracks(artist, title):
            try:
                lyrics = mediafile.MediaFile(track.path).lyrics
            except mediafile.UnreadableFileError as e:
                logger.warning("Can't read tags of %s: %s", track.path, e)
                continue

            if lyrics is None:
                continue

            lyrics = lyrics.replace("\x00", "").strip()
            if lyrics:
                logger.debug("Found lyrics in file metadata: %s", track.path)
                return Lyrics(track.album.artist.name, track.title, lyrics)

        return None


PROVIDER = EmbeddedLyricsProvider
