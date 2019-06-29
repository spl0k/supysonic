#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .test_login import LoginTestCase
from .test_folder import FolderTestCase
from .test_playlist import PlaylistTestCase
from .test_user import UserTestCase


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(LoginTestCase))
    suite.addTest(unittest.makeSuite(FolderTestCase))
    suite.addTest(unittest.makeSuite(PlaylistTestCase))
    suite.addTest(unittest.makeSuite(UserTestCase))

    return suite
