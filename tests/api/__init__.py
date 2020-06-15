# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .test_response_helper import suite as rh_suite
from .test_api_setup import ApiSetupTestCase
from .test_system import SystemTestCase
from .test_user import UserTestCase
from .test_chat import ChatTestCase
from .test_search import SearchTestCase
from .test_playlist import PlaylistTestCase
from .test_browse import BrowseTestCase
from .test_album_songs import AlbumSongsTestCase
from .test_annotation import AnnotationTestCase
from .test_media import MediaTestCase
from .test_transcoding import TranscodingTestCase
from .test_radio import RadioStationTestCase


def suite():
    suite = unittest.TestSuite()

    suite.addTest(rh_suite())
    suite.addTest(unittest.makeSuite(ApiSetupTestCase))
    suite.addTest(unittest.makeSuite(SystemTestCase))
    suite.addTest(unittest.makeSuite(UserTestCase))
    suite.addTest(unittest.makeSuite(ChatTestCase))
    suite.addTest(unittest.makeSuite(SearchTestCase))
    suite.addTest(unittest.makeSuite(PlaylistTestCase))
    suite.addTest(unittest.makeSuite(BrowseTestCase))
    suite.addTest(unittest.makeSuite(AlbumSongsTestCase))
    suite.addTest(unittest.makeSuite(AnnotationTestCase))
    suite.addTest(unittest.makeSuite(MediaTestCase))
    suite.addTest(unittest.makeSuite(TranscodingTestCase))
    suite.addTest(unittest.makeSuite(RadioStationTestCase))

    return suite
