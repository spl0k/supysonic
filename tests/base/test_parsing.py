# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.utils import ensure_list, ensure_str, parse_bool, parse_float, parse_int


class ParsingTestCase(unittest.TestCase):
    def test_bool_absent(self):
        self.assertIsNone(parse_bool(None))
        self.assertIsNone(parse_bool(""))

    def test_bool_true(self):
        for value in ("true", "True", "TRUE", "yes", "YES", "on", "1"):
            self.assertTrue(parse_bool(value), value)

    def test_bool_false(self):
        for value in ("false", "False", "FALSE", "no", "NO", "off", "0"):
            self.assertFalse(parse_bool(value), value)

    def test_bool_invalid(self):
        for value in ("maybe", "2", "-1", "tru", "checked", "selected"):
            with self.assertRaises(ValueError, msg=value):
                parse_bool(value)

    def test_int(self):
        self.assertIsNone(parse_int(None))
        self.assertIsNone(parse_int(""))
        self.assertEqual(parse_int("42"), 42)
        self.assertEqual(parse_int("-42"), -42)
        self.assertEqual(parse_int(42), 42)

    def test_int_invalid(self):
        for value in ("huge", "4.2", "0x10", "one"):
            with self.assertRaises(ValueError, msg=value):
                parse_int(value)

    def test_int_beyond_float_range(self):
        # too large to convert to a float, which rules out sharing the float
        # path's finiteness check
        huge = "9" * 400
        self.assertEqual(parse_int(huge), int(huge))
        with self.assertRaises(ValueError):
            parse_int(huge, max=10)

    def test_int_bounds(self):
        self.assertEqual(parse_int("5", min=0, max=10), 5)
        self.assertEqual(parse_int("0", min=0, max=10), 0)
        self.assertEqual(parse_int("10", min=0, max=10), 10)

        with self.assertRaises(ValueError):
            parse_int("-1", min=0)
        with self.assertRaises(ValueError):
            parse_int("11", max=10)

    def test_float(self):
        self.assertIsNone(parse_float(None))
        self.assertIsNone(parse_float(""))
        self.assertEqual(parse_float("0.5"), 0.5)
        self.assertEqual(parse_float("1"), 1.0)

    def test_float_invalid(self):
        for value in ("loud", "nan", "inf", "-inf", "Infinity"):
            with self.assertRaises(ValueError, msg=value):
                parse_float(value)

    def test_float_bounds(self):
        self.assertEqual(parse_float("0.5", min=0, max=1), 0.5)

        with self.assertRaises(ValueError):
            parse_float("-0.1", min=0)
        with self.assertRaises(ValueError):
            parse_float("1.1", max=1)

    def test_ensure_str(self):
        ensure_str("")
        ensure_str("/music")

        for value in (None, 42, b"/music", ["/music"]):
            with self.assertRaises(TypeError, msg=repr(value)):
                ensure_str(value)

    def test_ensure_list(self):
        ensure_list([])
        ensure_list(["/music"])
        ensure_list(("/music",))

        for value in (None, 42, "/music", {"/music"}):
            with self.assertRaises(TypeError, msg=repr(value)):
                ensure_list(value)


if __name__ == "__main__":
    unittest.main()
