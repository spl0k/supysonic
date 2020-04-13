# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2019 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from . import base
from . import managers
from . import api
from . import frontend

from .issue85 import Issue85TestCase
from .issue101 import Issue101TestCase
from .issue129 import Issue129TestCase
from .issue133 import Issue133TestCase
from .issue139 import Issue139TestCase
from .issue148 import Issue148TestCase


def suite():
    suite = unittest.TestSuite()

    suite.addTest(base.suite())
    suite.addTest(managers.suite())
    suite.addTest(api.suite())
    suite.addTest(frontend.suite())
    suite.addTest(unittest.makeSuite(Issue85TestCase))
    suite.addTest(unittest.makeSuite(Issue101TestCase))
    suite.addTest(unittest.makeSuite(Issue129TestCase))
    suite.addTest(unittest.makeSuite(Issue133TestCase))
    suite.addTest(unittest.makeSuite(Issue139TestCase))
    suite.addTest(unittest.makeSuite(Issue148TestCase))

    return suite
