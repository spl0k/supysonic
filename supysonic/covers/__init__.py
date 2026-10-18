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
from .exceptions import CoverArtProviderImportError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Cover:
    """A cover art image, either a file on disk or its raw contents.

    Exactly one of ``path`` and ``data`` is set. Either way the image format is
    read off the contents, so neither needs to come with a mimetype.
    """

    path: str | None = None
    data: bytes | None = None

    def __post_init__(self):
        if (self.path is None) == (self.data is None):
            raise ValueError("A cover is either a path or data, exactly one of them")


class CoverArtProvider(ABC):
    """A source of cover art.

    A provider takes part in two distinct moments. When entities are
    serialized, :meth:`find_covers` tells which of them it has a cover for, and
    under which id: that id is what clients get as ``coverArt``. When a client
    then asks for that id, :meth:`get_cover` is given the entity it names and
    hands the image over.

    Subclasses are self-contained: they own their configuration section and
    whatever they need to find covers.
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
    def find_covers(self, entities):
        """Tell which of ``entities`` this provider has a cover for.

        Called on every serialization, for whole collections at once: it must
        be cheap, relying on what's in the database rather than on files or
        remote services.

        The id announced for an entity is either its own, when the cover
        belongs to it, or the id of another entity the cover belongs to, as a
        fallback: a track may show the cover of its folder. Whatever the case,
        :meth:`get_cover` must then answer for the entity that id names.

        :param entities: :class:`~supysonic.db.models.Folder`,
            :class:`~supysonic.db.models.Artist`,
            :class:`~supysonic.db.models.Album` or
            :class:`~supysonic.db.models.Track` instances, all of the same
            type. A provider having nothing for a type returns an empty
            ``dict`` for it, without querying anything.
        :returns: a ``dict`` mapping the id of each entity this provider has a
            cover for to the id of the entity the cover belongs to. Entities
            left out have no cover from this provider.
        """

    @abstractmethod
    def get_cover(self, entity):
        """The cover belonging to ``entity``.

        Only the entity's own cover: falling back on a related entity is done
        by :meth:`find_covers`, announcing that entity's id instead.

        Not having one is not an error, and neither is a file that can't be
        read: both are reasons to return ``None``, logging at most, so the next
        provider gets its chance.

        :param entity: a :class:`~supysonic.db.models.Folder`,
            :class:`~supysonic.db.models.Artist`,
            :class:`~supysonic.db.models.Album` or
            :class:`~supysonic.db.models.Track`.
        :returns: a :class:`Cover`, or ``None``.
        """


def announce_covers(providers, entities):
    """The cover id to announce for each of ``entities``, by entity id.

    An entity's own cover is preferred over one it falls back on, whatever the
    provider order: the first provider offering an own cover wins. Keys and
    values are strings.
    """

    pending = {str(e.id): e for e in entities}
    fallbacks = {}
    owned = {}

    for provider in providers:
        if not pending:
            break

        for eid, cover_id in provider.find_covers(list(pending.values())).items():
            eid, cover_id = str(eid), str(cover_id)
            if eid not in pending:  # Not what was asked, shouldn't happen
                continue

            if cover_id == eid:
                owned[eid] = cover_id
                del pending[eid]
            else:
                fallbacks.setdefault(eid, cover_id)

    return fallbacks | owned


def load_cover_art_providers(config):
    """Build the providers listed by the ``cover_art_providers`` config option.

    A listed provider that isn't properly configured is left out, with a
    warning, as if it hadn't been listed at all.
    """

    return load_extensions(
        config.webapp.cover_art_providers,
        config,
        logger=logger,
        package=__name__,
        attribute="PROVIDER",
        base=CoverArtProvider,
        error=CoverArtProviderImportError,
        kind="cover art provider",
    )
