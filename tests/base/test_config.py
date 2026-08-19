# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import tempfile
import unittest

from supysonic.config import DefaultConfig, IniConfig


class ConfigTestCase(unittest.TestCase):
    def __write_config(self, contents):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".ini", delete=False, encoding="utf-8"
        ) as f:
            f.write(contents)
            path = f.name
        self.addCleanup(os.remove, path)
        return path

    def test_existing_section_merges_into_defaults(self):
        # A section name matching a default dict (e.g. BASE) is merged into it,
        # overriding only the listed keys and preserving the rest.
        path = self.__write_config("[BASE]\nscanner_extensions = mp3 flac\n")

        conf = IniConfig(path)
        self.assertEqual(conf.BASE["scanner_extensions"], "mp3 flac")
        # Untouched defaults survive the merge
        self.assertIn("database_uri", conf.BASE)

        # ... and the merge happens on the instance only, leaving the class-level
        # defaults (and any config built later) alone
        self.assertIsNone(DefaultConfig.BASE["scanner_extensions"])
        self.assertIsNone(DefaultConfig().BASE["scanner_extensions"])

    def test_sections(self):
        conf = IniConfig("tests/assets/sample.ini")
        for attr in ("UNKNOWN", "ISSUE84"):
            self.assertTrue(hasattr(conf, attr))
            self.assertIsInstance(getattr(conf, attr), dict)

    def test_unknown_section_keeps_strings(self):
        # Values of sections we know nothing about are never coerced
        conf = IniConfig("tests/assets/sample.ini")

        for value in conf.UNKNOWN.values():
            self.assertIsInstance(value, str)
        self.assertEqual(conf.UNKNOWN["int"], "42")
        self.assertEqual(conf.UNKNOWN["yn_true"], "yes")

    def test_typed_keys(self):
        path = self.__write_config(
            "[base]\nfollow_symlinks = yes\n"
            "[webapp]\ncache_size = 512\ntranscode_cache_size = 1024\n"
            "mount_api = off\nmount_webui = 1\nlog_rotate = no\n"
            "[daemon]\nrun_watcher = true\nwait_delay = 0.5\n"
        )
        conf = IniConfig(path)

        self.assertIs(conf.BASE["follow_symlinks"], True)
        self.assertEqual(conf.WEBAPP["cache_size"], 512)
        self.assertEqual(conf.WEBAPP["transcode_cache_size"], 1024)
        self.assertIs(conf.WEBAPP["mount_api"], False)
        self.assertIs(conf.WEBAPP["mount_webui"], True)
        self.assertIs(conf.WEBAPP["log_rotate"], False)
        self.assertIs(conf.DAEMON["run_watcher"], True)
        self.assertEqual(conf.DAEMON["wait_delay"], 0.5)

    def test_string_keys_arent_coerced(self):
        # Regression: string values that look like numbers or booleans used to be
        # silently converted, breaking str operations on them
        path = self.__write_config(
            "[lastfm]\napi_key = 1234567890\nsecret = 0987654321\n"
            "[webapp]\nlog_level = 1\nindex_ignored_prefixes = 1 2 3\n"
            "[transcoding]\ndefault_transcode_target = 3\n"
            "[mimetypes]\nfoo = on\n"
        )
        conf = IniConfig(path)

        self.assertEqual(conf.LASTFM["api_key"], "1234567890")
        self.assertEqual(conf.LASTFM["secret"], "0987654321")
        self.assertEqual(conf.WEBAPP["log_level"], "1")
        self.assertEqual(conf.WEBAPP["index_ignored_prefixes"], "1 2 3")
        self.assertEqual(conf.TRANSCODING["default_transcode_target"], "3")
        self.assertEqual(conf.MIMETYPES["foo"], "on")

    def test_invalid_typed_value(self):
        for section, option in (
            ("webapp", "cache_size = lots"),
            ("webapp", "cache_size = -1"),
            ("daemon", "run_watcher = maybe"),
            ("daemon", "wait_delay = soon"),
            ("daemon", "wait_delay = nan"),
        ):
            path = self.__write_config(f"[{section}]\n{option}\n")
            key = option.split(" ", 1)[0]
            with self.subTest(option=option):
                with self.assertRaises(ValueError) as cm:
                    IniConfig(path)
                self.assertIn(f"{section.upper()}.{key}", str(cm.exception))

    def test_no_interpolation(self):
        conf = IniConfig("tests/assets/sample.ini")

        self.assertEqual(conf.ISSUE84["variable"], "value")
        self.assertEqual(conf.ISSUE84["key"], "some value with a %variable")


if __name__ == "__main__":
    unittest.main()
