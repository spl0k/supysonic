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
    models holding their persisted data, the routes linking and unlinking an
    account and the template injected in the user profile page.
    """

    name = None
    """Short identifier used in config, blueprint name and routes"""

    blueprint = None

    models = ()
    """Database models used to persist state"""

    @abstractmethod
    def __init__(self, config):
        """Build the scrobbler off the whole ``config``.

        Subclasses read their own section out of it, with
        ``config.section(TheirSection)``.
        """

    @property
    def profile_template(self):
        """The template rendering this scrobbler's profile page fragment."""

        return f"{self.name}/profile.html"

    @property
    @abstractmethod
    def enabled(self):
        """Whether the service is configured well enough to be usable."""

    @abstractmethod
    def link_account(self, user, token):
        """Link ``user``'s account to the service, and persist the link.

        Raises a :class:`~supysonic.scrobblers.exceptions.ScrobblerError` if the
        link couldn't be established.
        """

    @abstractmethod
    def unlink_account(self, user):
        """Forget ``user``'s account link, if there's one."""

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
    """Build the scrobblers listed by the ``scrobblers`` config option."""

    scrobblers = []
    for name in config.webapp.scrobblers:
        cls = _load_class(name)
        scrobbler = cls(config)
        if not scrobbler.enabled:
            logger.warning(
                "Scrobbler %r is enabled but isn't properly configured", name
            )
        scrobblers.append(scrobbler)

    return scrobblers
