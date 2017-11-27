# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import sys
import unittest

from supysonic.config import DefaultConfig
from supysonic.managers.user import UserManager
from supysonic.web import create_application, store

class TestConfig(DefaultConfig):
    TESTING = True
    LOGGER_HANDLER_POLICY = 'never'
    BASE = {
        'database_uri': 'sqlite:',
        'scanner_extensions': None
    }
    MIMETYPES = {
        'mp3': 'audio/mpeg',
        'weirdextension': 'application/octet-stream'
    }

    def __init__(self, with_webui, with_api):
        super(TestConfig, self).__init__

        self.WEBAPP.update({
            'mount_webui': with_webui,
            'mount_api': with_api
        })

class TestBase(unittest.TestCase):
    __with_webui__ = False
    __with_api__ = False

    def setUp(self):
        app = create_application(TestConfig(self.__with_webui__, self.__with_api__))
        self.__ctx = app.app_context()
        self.__ctx.push()

        self.store = store
        with io.open('schema/sqlite.sql', 'r') as sql:
            schema = sql.read()
            for statement in schema.split(';'):
                self.store.execute(statement)

        self.client = app.test_client()

        UserManager.add(self.store, 'alice', 'Alic3', 'test@example.com', True)
        UserManager.add(self.store, 'bob', 'B0b', 'bob@example.com', False)

    def tearDown(self):
        self.__ctx.pop()

        to_unload = [ m for m in sys.modules if m.startswith('supysonic') ]
        for m in to_unload:
            del sys.modules[m]

