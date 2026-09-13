# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from lxml import etree

from .apitestbase import ApiTestBase


class SystemTestCase(ApiTestBase):
    def test_ping(self):
        rv, _ = self._make_request("ping")
        # Clients ping to discover the server's API version
        xml = etree.fromstring(rv.data)
        self.assertEqual(xml.get("status"), "ok")
        self.assertEqual(xml.get("version"), self.apiVersion)

    def test_get_license(self):
        rv, child = self._make_request("getLicense", tag="license")
        self.assertEqual(child.get("valid"), "true")


if __name__ == "__main__":
    unittest.main()
