#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Óscar García Amor <ogarcia@connectical.com>
#
# Distributed under terms of the GNU GPLv3 license.

from .test_folder_manager import FolderManagerTestCase
from .test_user_manager import UserManagerTestCase

import unittest

def suite():
    suite = unittest.TestSuite()
    suite.addTest(FolderManagerTestCase())
    suite.addTest(UserManagerTestCase())
    return suite
