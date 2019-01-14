# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

import os
import tempfile

class DefaultConfig(object):
    DEBUG = False

    tempdir = os.path.join(tempfile.gettempdir(), 'supysonic')
    BASE = {
        'database_uri': 'sqlite:///' + os.path.join(tempdir, 'supysonic.db'),
        'scanner_extensions': None
    }
    WEBAPP = {
        'cache_dir': tempdir,
        'cache_size': 1024,
        'transcode_cache_size': 512,
        'log_file': None,
        'log_level': 'WARNING',

        'mount_webui': True,
        'mount_api': True
    }
    DAEMON = {
        'wait_delay': 5,
        'log_file': None,
        'log_level': 'WARNING'
    }
    LASTFM = {
        'api_key': None,
        'secret': None
    }
    TRANSCODING = {}
    MIMETYPES = {}

class IniConfig(DefaultConfig):
    common_paths = [
        '/etc/supysonic',
        os.path.expanduser('~/.supysonic'),
        os.path.expanduser('~/.config/supysonic/supysonic.conf'),
        'supysonic.conf'
    ]

    def __init__(self, paths):
        parser = RawConfigParser()
        parser.read(paths)

        for section in parser.sections():
            options = { k: self.__try_parse(v) for k, v in parser.items(section) }
            section = section.upper()

            if hasattr(self, section):
                getattr(self, section).update(options)
            else:
                setattr(self, section, options)

    @staticmethod
    def __try_parse(value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                lv = value.lower()
                if lv in ('yes', 'true', 'on'):
                    return True
                elif lv in ('no', 'false', 'off'):
                    return False
                return value

    @classmethod
    def from_common_locations(cls):
        return IniConfig(cls.common_paths)

