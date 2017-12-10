# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .test_db import DbTestCase
from .test_scanner import ScannerTestCase
from .test_watcher import suite as watcher_suite
from .test_cli import CLITestCase

def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(DbTestCase))
    suite.addTest(unittest.makeSuite(ScannerTestCase))
    suite.addTest(watcher_suite())
    suite.addTest(unittest.makeSuite(CLITestCase))

    return suite

