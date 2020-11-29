# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from .apitestbase import ApiTestBase


class SystemTestCase(ApiTestBase):
    def test_ping(self):
        self._make_request("ping")

    def test_get_license(self):
        rv, child = self._make_request("getLicense", tag="license")
        self.assertEqual(child.get("valid"), "true")


if __name__ == "__main__":
    unittest.main()
