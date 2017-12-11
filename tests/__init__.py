# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from . import base, managers, api, frontend

def suite():
    suite = unittest.TestSuite()

    suite.addTest(base.suite())
    suite.addTest(managers.suite())
    suite.addTest(api.suite())
    suite.addTest(frontend.suite())

    return suite
