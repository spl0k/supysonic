# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Lyrics stored in a text file next to the track files."""

import logging
import os.path

from . import Lyrics, LyricsProvider
from ._tracks import candidate_tracks

logger = logging.getLogger(__name__)


class SidecarLyricsProvider(LyricsProvider):
    name = "sidecar"
    configured = True

    def __init__(self, config):
        pass

    def get_lyrics(self, artist, title):
        for track in candidate_tracks(artist, title):
            # A text file with the same name as the track
            lyrics_path = os.path.splitext(track.path)[0] + ".txt"
            if not os.path.exists(lyrics_path):
                continue

            try:
                with open(lyrics_path) as f:
                    lyrics = f.read()
            except UnicodeError:
                # Rather than failing, try the next candidates
                logger.warning("Unsupported encoding for lyrics file %s", lyrics_path)
                continue
            except OSError as e:
                logger.warning("Can't read lyrics file %s: %s", lyrics_path, e)
                continue

            logger.debug("Found lyrics file: %s", lyrics_path)
            return Lyrics(track.album.artist.name, track.title, lyrics)

        return None


PROVIDER = SidecarLyricsProvider
