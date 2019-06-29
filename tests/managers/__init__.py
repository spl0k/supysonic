# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .test_manager_folder import FolderManagerTestCase
from .test_manager_user import UserManagerTestCase


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(FolderManagerTestCase))
    suite.addTest(unittest.makeSuite(UserManagerTestCase))

    return suite
