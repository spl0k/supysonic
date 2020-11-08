# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .api.test_lyrics import LyricsTestCase
from .base.test_lastfm import LastFmTestCase


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(LastFmTestCase))
    suite.addTest(unittest.makeSuite(LyricsTestCase))

    return suite
