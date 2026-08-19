# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import sys
import tempfile
from configparser import RawConfigParser
from functools import partial

from .utils import parse_bool, parse_float, parse_int

current_config = None


def get_current_config():
    global current_config
    return current_config or DefaultConfig()


_VALUE_PARSERS = {
    "BASE": {"follow_symlinks": parse_bool},
    "WEBAPP": {
        "cache_size": partial(parse_int, min=0),
        "transcode_cache_size": partial(parse_int, min=0),
        "log_rotate": parse_bool,
        "mount_webui": parse_bool,
        "mount_api": parse_bool,
    },
    "DAEMON": {
        "run_watcher": parse_bool,
        "wait_delay": partial(parse_float, min=0),
        "log_rotate": parse_bool,
    },
}


class DefaultConfig:
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    tempdir = os.path.join(tempfile.gettempdir(), "supysonic")
    BASE = {
        "database_uri": "sqlite:///" + os.path.join(tempdir, "supysonic.db"),
        "scanner_extensions": None,
        "follow_symlinks": False,
    }
    WEBAPP = {
        "cache_dir": tempdir,
        "cache_size": 1024,
        "transcode_cache_size": 512,
        "log_file": None,
        "log_level": "WARNING",
        "log_rotate": True,
        "mount_webui": True,
        "mount_api": True,
        "index_ignored_prefixes": "El La Le Las Les Los The",
    }
    DAEMON = {
        "socket": (
            r"\\.\pipe\supysonic"
            if sys.platform == "win32"
            else os.path.join(tempdir, "supysonic.sock")
        ),
        "run_watcher": True,
        "wait_delay": 5,
        "jukebox_command": None,
        "log_file": None,
        "log_level": "WARNING",
        "log_rotate": True,
    }
    LASTFM = {"api_key": None, "secret": None}
    LISTENBRAINZ = {"api_url": "https://api.listenbrainz.org"}
    TRANSCODING = {}
    MIMETYPES = {}

    def __init__(self):
        global current_config

        for attr in dir(self):
            if attr.isupper() and isinstance(getattr(self, attr), dict):
                setattr(self, attr, getattr(self, attr).copy())

        current_config = self


class IniConfig(DefaultConfig):
    common_paths = [
        "/etc/supysonic",
        os.path.expanduser("~/.supysonic"),
        os.path.expanduser("~/.config/supysonic/supysonic.conf"),
        "supysonic.conf",
    ]

    def __init__(self, paths):
        super().__init__()

        parser = RawConfigParser()
        parser.read(paths)

        for name in parser.sections():
            section = name.upper()
            parsers = _VALUE_PARSERS.get(section, {})
            options = {
                k: self.__parse(section, k, v, parsers.get(k))
                for k, v in parser.items(name)
            }

            if hasattr(self, section):
                getattr(self, section).update(options)
            else:
                setattr(self, section, options)

    @staticmethod
    def __parse(section, key, value, parser):
        if parser is None:
            return value

        try:
            return parser(value)
        except ValueError as e:
            raise ValueError(
                f"Invalid value for {section}.{key}: {value!r} ({e})"
            ) from e

    @classmethod
    def from_common_locations(cls):
        return IniConfig(cls.common_paths)
