# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import unittest
import sys

from supysonic.managers.user import UserManager

from .appmock import AppMock

class TestBase(unittest.TestCase):
    def setUp(self):
        app_mock = AppMock()
        self.app = app_mock.app
        self.store = app_mock.store
        self.client = self.app.test_client()

        sys.modules['supysonic.web'] = app_mock
        importlib.import_module(self.__module_to_test__)

        UserManager.add(self.store, 'alice', 'Alic3', 'test@example.com', True)
        UserManager.add(self.store, 'bob', 'B0b', 'bob@example.com', False)

    def tearDown(self):
        self.store.close()
        to_unload = [ m for m in sys.modules if m.startswith('supysonic') ]
        for m in to_unload:
            del sys.modules[m]

