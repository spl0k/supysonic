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

from .test_response_helper import suite as rh_suite

def suite():
    suite = unittest.TestSuite()

    suite.addTest(rh_suite())

    return suite

