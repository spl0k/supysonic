# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from abc import ABC, abstractmethod
from importlib import import_module

from flask import Blueprint

from ..db.proxy import db
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
    """Short identifier used in config, blueprint name and routes"""

    blueprint = None
    """Flask blueprint carrying this scrobbler's routes, if it has any"""

    profile_template = None
    """The template rendering this scrobbler's profile page fragment.

    Should be named after the scrobbler. None for a scrobbler with nothing to
    show there.
    """

    models = ()
    """Database models used to persist state"""

    @abstractmethod
    def __init__(self, config):
        """Build the scrobbler off the whole ``config``.

        Subclasses read their own section out of it, with
        ``config.section(TheirSection)``.
        """

    @property
    @abstractmethod
    def configured(self):
        """Whether the service was given what it needs to be usable."""

    @abstractmethod
    def is_linked(self, user):
        """Whether ``user`` has a link the service hasn't rejected."""

    @abstractmethod
    def now_playing(self, user, track, client):
        """Report ``user`` as currently playing ``track``."""

    @abstractmethod
    def scrobble(self, user, track, ts, client):
        """Report ``user`` as having played ``track`` at ``ts``."""

    def create_tables(self):
        """Create the tables backing :attr:`models` if they're missing."""

        if self.models:
            db.create_tables(self.models, safe=True)


def _load_class(name):
    """Import the scrobbler class configured as ``name``.

    A bare name is one of the scrobblers provided by Supysonic, anything with a
    dot is the path of a module to import as-is.
    """

    module_name = name if "." in name else f"{__name__}.{name}"

    try:
        module = import_module(module_name)
    except ImportError as e:
        raise ScrobblerImportError(f"Can't import scrobbler {name!r}: {e}") from e

    cls = getattr(module, "SCROBBLER", None)
    if cls is None:
        raise ScrobblerImportError(f"Module {module_name!r} defines no SCROBBLER")

    if not (isinstance(cls, type) and issubclass(cls, Scrobbler)):
        raise ScrobblerImportError(
            f"SCROBBLER of {module_name!r} isn't a Scrobbler subclass"
        )

    return cls


def load_scrobblers(config):
    """Build the scrobblers listed by the ``scrobblers`` config option.

    A listed scrobbler that isn't properly configured is left out rather than
    loaded half-working: it gets no routes and no section on the profile page,
    as if it hadn't been listed at all. Only a warning tells it apart, since
    being listed says it was meant to work.
    """

    scrobblers = []
    for name in config.webapp.scrobblers:
        cls = _load_class(name)
        scrobbler = cls(config)
        if not scrobbler.configured:
            logger.warning(
                "Scrobbler %r isn't properly configured, it won't be loaded", name
            )
        else:
            scrobblers.append(scrobbler)

    return scrobblers
