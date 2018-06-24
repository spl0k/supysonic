# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from . import base
from . import managers
from . import api
from . import frontend

from .issue101 import Issue101TestCase

def suite():
    suite = unittest.TestSuite()

    suite.addTest(base.suite())
    suite.addTest(managers.suite())
    suite.addTest(api.suite())
    suite.addTest(frontend.suite())
    suite.addTest(unittest.makeSuite(Issue101TestCase))

    return suite

