# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from abc import ABC, abstractmethod

from flask import Blueprint

from ..db.proxy import db
from ..extensions import load_extensions
from .exceptions import ScrobblerImportError

logger = logging.getLogger(__name__)


def make_blueprint(name, import_name):
    """Build the blueprint of the scrobbler called ``name``."""

    from ..frontend._helpers import login_check

    blueprint = Blueprint(
        name,
        import_name,
        template_folder="templates",
        url_prefix=f"/scrobbler/{name}",
    )
    blueprint.before_request(login_check)

    return blueprint


class Scrobbler(ABC):
    """A service playback is reported to.

    Subclasses are self-contained: they own their configuration section, the
    models holding their persisted data, the routes they need and the template
    injected in the user profile page.

    Only the reporting methods below are called from outside. Linking an
    account is between a scrobbler and its own views, which is why no signature
    for it is imposed here: what it takes is the service's business.
    """

    name = None
    """Short identifier used as the blueprint name and in the routes.

    Not the name to list in the configuration file, which is the module path.
    """

    blueprint = None
    """Flask blueprint carrying this scrobbler's routes, if it has any"""

    profile_template = None
    """The template rendering this scrobbler's profile page fragment.

    Should be named after the scrobbler. None for a scrobbler with nothing to
    show there.
    """

    models = ()
    """Database models used to persist state, created by :meth:`create_tables`"""

    @abstractmethod
    def __init__(self, config):
        """Build the scrobbler off the whole ``config``.

        Subclasses read their own section out of it, with
        ``config.section(TheirSection)``.

        :param config: whole :class:`~supysonic.config.Config` instance.
        """

    @property
    @abstractmethod
    def configured(self):
        """Whether the service was given what it needs to be usable.

        One saying no isn't loaded at all. A scrobbler needing no configuration
        simply says yes.
        """

    @abstractmethod
    def is_linked(self, user):
        """Whether ``user`` has a link the service hasn't rejected.

        This is what the Subsonic API reports as ``scrobblingEnabled``, which is
        true as soon as any loaded scrobbler says so.

        :param user: :class:`~supysonic.db.models.User` model
        """

    @abstractmethod
    def now_playing(self, user, track, client):
        """Report ``user`` as currently playing ``track`` on ``client``.

        Fire-and-forget, see :meth:`scrobble`.

        :param user: :class:`~supysonic.db.models.User` model
        :param track: :class:`~supysonic.db.models.Track` model
        :param client: Name of the client they're playing with.
        """

    @abstractmethod
    def scrobble(self, user, track, ts, client):
        """Report ``user`` as having played ``track`` on ``client`` at ``ts``.

        Fire-and-forget: a user who hasn't linked their account, a service
        that's down or credentials that got rejected are all reasons to give up
        quietly, logging at most. Raising would turn a played track into an API
        error on the client side.

        :param user: :class:`~supysonic.db.models.User` model
        :param track: :class:`~supysonic.db.models.Track` model
        :param client: Name of the client they're playing with.
        :param ts: Unix timestamp the track was played at.
        """

    def create_tables(self):
        """Create the tables backing :attr:`models` if they're missing."""

        if self.models:
            db.create_tables(self.models, safe=True)


def load_scrobblers(config):
    """Build the scrobblers listed by the ``scrobblers`` config option.

    A listed scrobbler that isn't properly configured is left out rather than
    loaded half-working: it gets no routes and no section on the profile page,
    as if it hadn't been listed at all. Only a warning tells it apart, since
    being listed says it was meant to work.
    """

    return load_extensions(
        config.webapp.scrobblers,
        config,
        logger=logger,
        package=__name__,
        attribute="SCROBBLER",
        base=Scrobbler,
        error=ScrobblerImportError,
        kind="scrobbler",
    )
