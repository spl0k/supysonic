# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import tempfile
import unittest

from supysonic.config import IniConfig


class ConfigTestCase(unittest.TestCase):
    def test_existing_section_merges_into_defaults(self):
        # A section name matching a default dict (e.g. BASE) is merged into it,
        # overriding only the listed keys and preserving the rest.
        with tempfile.NamedTemporaryFile(
            "w", suffix=".ini", delete=False, encoding="utf-8"
        ) as f:
            f.write("[BASE]\nscanner_extensions = mp3 flac\n")
            path = f.name
        self.addCleanup(os.remove, path)

        conf = IniConfig(path)
        self.assertEqual(conf.BASE["scanner_extensions"], "mp3 flac")
        # Untouched defaults survive the merge
        self.assertIn("database_uri", conf.BASE)

    def test_sections(self):
        conf = IniConfig("tests/assets/sample.ini")
        for attr in ("TYPES", "BOOLEANS"):
            self.assertTrue(hasattr(conf, attr))
            self.assertIsInstance(getattr(conf, attr), dict)

    def test_types(self):
        conf = IniConfig("tests/assets/sample.ini")

        self.assertIsInstance(conf.TYPES["float"], float)
        self.assertIsInstance(conf.TYPES["int"], int)
        self.assertIsInstance(conf.TYPES["string"], str)

        for t in ("bool", "switch", "yn"):
            self.assertIsInstance(conf.BOOLEANS[t + "_false"], bool)
            self.assertIsInstance(conf.BOOLEANS[t + "_true"], bool)
            self.assertFalse(conf.BOOLEANS[t + "_false"])
            self.assertTrue(conf.BOOLEANS[t + "_true"])

    def test_no_interpolation(self):
        conf = IniConfig("tests/assets/sample.ini")

        self.assertEqual(conf.ISSUE84["variable"], "value")
        self.assertEqual(conf.ISSUE84["key"], "some value with a %variable")


if __name__ == "__main__":
    unittest.main()
