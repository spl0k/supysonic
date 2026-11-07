# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os
import sys
import tempfile
from collections.abc import Mapping
from configparser import RawConfigParser
from functools import partial

from .parsers import (
    parse_bool,
    parse_extensions,
    parse_float,
    parse_format,
    parse_int,
    parse_words,
)

logger = logging.getLogger(__name__)


class Option:
    """A single configuration value, declaring its default and its parser.

    ``formerly`` names, as ``"section.key"``, where an option that has been
    moved used to live. A value found there is still honored, with a warning,
    as long as the new location doesn't set one.
    """

    def __init__(self, default=None, parser=None, *, formerly=None):
        self.default = default
        self.parser = parser
        self.formerly = tuple(formerly.split(".", 1)) if formerly else None
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._values[self.name]

    def parse(self, section, value):
        """Parse a user-provided value, or return it as-is when untyped."""

        if self.parser is None:
            return value

        try:
            parsed = self.parser(value)
            if parsed is None:
                raise ValueError("no value provided")
            return parsed
        except ValueError as e:
            raise ValueError(
                f"Invalid value for {section}.{self.name}: {value!r} ({e})"
            ) from e


class Section:
    """Base class for configuration sections.

    A subclass declares its options as class attributes and the name of the
    config file section it reads through the ``section`` class keyword::

        class DaemonSection(Section, section="daemon"):
            run_watcher = Option(True, parse_bool)
    """

    __section__ = None
    __options__ = {}

    def __init_subclass__(cls, /, section=None, **kwargs):
        super().__init_subclass__(**kwargs)

        if section is not None:
            cls.__section__ = section

        # Walking the MRO rather than just this class' own attributes is what
        # lets mixins (LoggingOptions) contribute their options.
        options = {}
        for klass in reversed(cls.__mro__):
            for key, value in vars(klass).items():
                if isinstance(value, Option):
                    options[key] = value
        cls.__options__ = options

    def __init__(self, raw=None):
        raw = dict(raw) if raw else {}
        values = {
            key: (
                option.parse(self.__section__, raw[key])
                if key in raw
                else option.default
            )
            for key, option in self.__options__.items()
        }

        # Bypass the freezing below, and keep the unparsed values around for the
        # sections whose keys are user-provided
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "_raw", raw)

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self).__name__} is read-only")

    def __repr__(self):
        values = ", ".join(f"{k}={v!r}" for k, v in self._values.items())
        return f"{type(self).__name__}({values})"

    def override(self, **values):
        """Return a copy of this section with some of its values replaced."""

        return type(self)({**self._raw, **values})


class MappingSection(Section, Mapping):
    """A section whose keys are all user-provided, hence declares no option."""

    def __getitem__(self, key):
        return self._raw[key]

    def __iter__(self):
        return iter(self._raw)

    def __len__(self):
        return len(self._raw)


_TEMPDIR = os.path.join(tempfile.gettempdir(), __package__)


class LoggingOptions:
    """Options shared by the sections configuring a logger."""

    log_file = Option()
    log_level = Option("WARNING")
    log_rotate = Option(True, parse_bool)


class BaseSection(Section, section="base"):
    database_uri = Option("sqlite:///" + os.path.join(_TEMPDIR, f"{__package__}.db"))
    scanner_extensions = Option((), parse_extensions)
    follow_symlinks = Option(False, parse_bool)


class WebappSection(LoggingOptions, Section, section="webapp"):
    cache_dir = Option(_TEMPDIR)
    cache_size = Option(512, partial(parse_int, min=0))
    transcode_cache_size = Option(1024, partial(parse_int, min=0))
    mount_webui = Option(True, parse_bool)
    mount_api = Option(True, parse_bool)


class ApiSection(Section, section="api"):
    use_http_error_status = Option(False, parse_bool)
    index_ignored_prefixes = Option(
        "El La Le Las Les Los The", formerly="webapp.index_ignored_prefixes"
    )


class PluginsSection(Section, section="plugins"):
    scrobblers = Option(("lastfm", "listenbrainz"), parse_words)
    lyrics = Option(("embedded", "sidecar"), parse_words)
    cover_art = Option(("folder", "embedded"), parse_words)


class DaemonSection(LoggingOptions, Section, section="daemon"):
    socket = Option(
        r"\\.\pipe\supysonic"
        if sys.platform == "win32"
        else os.path.join(_TEMPDIR, "supysonic.sock")
    )
    run_watcher = Option(True, parse_bool)
    wait_delay = Option(5, partial(parse_float, min=0))
    jukebox_command = Option()


class MimetypesSection(MappingSection, section="mimetypes"):
    """Maps file extensions to the mimetype to serve them with."""


class TranscodingSection(Section, section="transcoding"):
    """Transcoding command lines."""

    default_transcode_target = Option(None, parse_format)

    def resolve(self, src_suffix, dst_suffix):
        """Return the command lines converting ``src_suffix`` to ``dst_suffix``.

        The result is a ``(transcoder, decoder, encoder)`` tuple of which either
        the transcoder alone or the decoder/encoder pair is set. A transcoder
        specific to this conversion wins over a decoder/encoder pipeline, itself
        preferred to the catch-all transcoder. ``(None, None, None)`` means
        there's no way to do the conversion.
        """

        transcoder = self._raw.get(f"transcoder_{src_suffix}_{dst_suffix}")
        if transcoder:
            return transcoder, None, None

        decoder = self._raw.get(f"decoder_{src_suffix}") or self._raw.get("decoder")
        encoder = self._raw.get(f"encoder_{dst_suffix}") or self._raw.get("encoder")
        if decoder and encoder:
            return None, decoder, encoder

        return self._raw.get("transcoder") or None, None, None


_CORE_SECTIONS = (
    BaseSection,
    WebappSection,
    ApiSection,
    PluginsSection,
    DaemonSection,
    MimetypesSection,
    TranscodingSection,
)


class Config:
    """Configuration.

    Besides the core sections exposed as properties, any module can declare a
    :class:`Section` subclass and have it built from the same config file
    through :meth:`section`, allowing potential pluggable modules to define and
    read their own configuration.
    """

    common_paths = [
        "/etc/supysonic",
        os.path.expanduser("~/.supysonic"),
        os.path.expanduser("~/.config/supysonic/supysonic.conf"),
        "supysonic.conf",
    ]

    def __init__(self, raw=None):
        self._raw = {
            name.lower(): dict(options) for name, options in (raw or {}).items()
        }
        self._sections = {}

        # Build and cache core sections
        for section_cls in _CORE_SECTIONS:
            self.section(section_cls)

    @classmethod
    def from_ini(cls, paths):
        parser = RawConfigParser()
        parser.read(paths)

        return cls({name: dict(parser.items(name)) for name in parser.sections()})

    @classmethod
    def from_common_locations(cls):
        return cls.from_ini(cls.common_paths)

    def section(self, section_cls):
        """Return this config's instance of ``section_cls``.

        Builds and caches it the first time, returns the cached instance on
        subsequent calls.
        """

        instance = self._sections.get(section_cls)
        if instance is None:
            instance = section_cls(self.__raw_section(section_cls))
            self._sections[section_cls] = instance

        return instance

    def __raw_section(self, section_cls):
        """Return the raw values of ``section_cls``, including those still
        found at the former location of a moved option."""

        raw = dict(self._raw.get(section_cls.__section__, {}))
        for key, option in section_cls.__options__.items():
            if option.formerly is None:
                continue

            old_section, old_key = option.formerly
            old_raw = self._raw.get(old_section, {})
            if old_key not in old_raw:
                continue

            if key in raw:
                logger.warning(
                    "Both %s.%s and %s.%s are set, ignoring the latter",
                    section_cls.__section__,
                    key,
                    old_section,
                    old_key,
                )
            else:
                logger.warning(
                    "%s.%s has moved to %s.%s, please update your configuration",
                    old_section,
                    old_key,
                    section_cls.__section__,
                    key,
                )
                raw[key] = old_raw[old_key]

        return raw

    def override(self, section_cls, **values):
        """Replace a section with a copy of it holding ``values``.

        Sections being read-only, this is the one way to alter a config once
        it's been built, and exists for tests only.
        """

        self._sections[section_cls] = self.section(section_cls).override(**values)

    base = property(lambda self: self.section(BaseSection))
    webapp = property(lambda self: self.section(WebappSection))
    api = property(lambda self: self.section(ApiSection))
    plugins = property(lambda self: self.section(PluginsSection))
    daemon = property(lambda self: self.section(DaemonSection))
    mimetypes = property(lambda self: self.section(MimetypesSection))
    transcoding = property(lambda self: self.section(TranscodingSection))
