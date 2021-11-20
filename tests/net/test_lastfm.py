# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import unittest

from supysonic.lastfm import LastFm


class LastFmTestCase(unittest.TestCase):
    """Designed only to have coverage on the most important method"""

    def test_request(self):
        logging.getLogger("supysonic.lastfm").addHandler(logging.NullHandler())
        lastfm = LastFm({"api_key": "key", "secret": "secret"}, None)

        rv = lastfm._LastFm__api_request(False, method="dummy", accents="àéèùö")
        self.assertIsInstance(rv, dict)


if __name__ == "__main__":
    unittest.main()
