# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..extensions import load_extensions
from .exceptions import LyricsProviderImportError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Lyrics:
    """Lyrics found by a provider, along with what they were found for.

    The artist and title are the ones the provider matched, which may differ
    from the ones asked for: the search is loose, the answer isn't.
    """

    artist: str
    title: str
    text: str


class LyricsProvider(ABC):
    """A source of song lyrics.

    Providers are asked in the order they're listed, until one of them answers.
    Subclasses are self-contained: they own their configuration section and
    whatever they need to find lyrics.
    """

    name = None
    """Short identifier, mostly for logging.

    Not the name to list in the configuration file, which is the module path.
    """

    @abstractmethod
    def __init__(self, config):
        """Build the provider off the whole ``config``.

        Subclasses read their own section out of it, with
        ``config.section(TheirSection)``.

        :param config: whole :class:`~supysonic.config.Config` instance.
        """

    @property
    @abstractmethod
    def configured(self):
        """Whether the provider was given what it needs to be usable.

        One saying no isn't loaded at all. A provider needing no configuration
        simply says yes.
        """

    @abstractmethod
    def get_lyrics(self, artist, title):
        """Look for the lyrics of the song ``title`` by ``artist``.

        Both come as-is from the client, and are matched however loosely the
        provider sees fit.

        Not finding any is not an error, and neither is a service that's down or
        a file that can't be read: all are reasons to return ``None``, logging
        at most, so the next provider gets its chance. Raising would turn a
        lyrics lookup into an API error on the client side.

        :param artist: Name of the artist.
        :param title: Title of the song.
        :returns: a :class:`Lyrics` instance, or ``None``.
        """


def load_lyrics_providers(config):
    """Build the providers listed by the ``lyrics_providers`` config option.

    A listed provider that isn't properly configured is left out, with a
    warning, as if it hadn't been listed at all.
    """

    return load_extensions(
        config.webapp.lyrics_providers,
        config,
        logger=logger,
        package=__name__,
        attribute="PROVIDER",
        base=LyricsProvider,
        error=LyricsProviderImportError,
        kind="lyrics provider",
    )
