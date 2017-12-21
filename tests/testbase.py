# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import inspect
import io
import os
import shutil
import sys
import unittest
import tempfile

from supysonic.db import init_database, release_database
from supysonic.config import DefaultConfig
from supysonic.managers.user import UserManager
from supysonic.web import create_application

class TestConfig(DefaultConfig):
    TESTING = True
    LOGGER_HANDLER_POLICY = 'never'
    MIMETYPES = {
        'mp3': 'audio/mpeg',
        'weirdextension': 'application/octet-stream'
    }
    TRANSCODING = {
        'transcoder_mp3_mp3': 'echo -n %srcpath %outrate',
        'decoder_mp3': 'echo -n Pushing out some mp3 data...',
        'encoder_cat': 'cat -',
        'encoder_md5': 'md5sum'
    }

    def __init__(self, with_webui, with_api):
        super(TestConfig, self).__init__()

        for cls in reversed(inspect.getmro(self.__class__)):
            for attr, value in cls.__dict__.iteritems():
                if attr.startswith('_') or attr != attr.upper():
                    continue

                if isinstance(value, dict):
                    setattr(self, attr, value.copy())
                else:
                    setattr(self, attr, value)

        self.WEBAPP.update({
            'mount_webui': with_webui,
            'mount_api': with_api
        })

class TestBase(unittest.TestCase):
    __with_webui__ = False
    __with_api__ = False

    def setUp(self):
        self.__dbfile = tempfile.mkstemp()[1]
        self.__dir = tempfile.mkdtemp()
        config = TestConfig(self.__with_webui__, self.__with_api__)
        config.BASE['database_uri'] = 'sqlite:///' + self.__dbfile
        config.WEBAPP['cache_dir'] = self.__dir

        init_database(config.BASE['database_uri'], True)
        release_database()

        app = create_application(config)
        self.__ctx = app.app_context()
        self.__ctx.push()

        self.client = app.test_client()

        UserManager.add('alice', 'Alic3', 'test@example.com', True)
        UserManager.add('bob', 'B0b', 'bob@example.com', False)

    @staticmethod
    def __should_unload_module(module):
        if module.startswith('supysonic'):
            return not module.startswith('supysonic.db')
        return False

    def tearDown(self):
        self.__ctx.pop()
        release_database()
        shutil.rmtree(self.__dir)
        os.remove(self.__dbfile)

        to_unload = [ m for m in sorted(sys.modules) if self.__should_unload_module(m) ]
        for m in to_unload:
            del sys.modules[m]

