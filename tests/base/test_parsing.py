# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.parsers import (
    MAIL_MAX_LENGTH,
    ensure_list,
    ensure_str,
    parse_bool,
    parse_float,
    parse_int,
    parse_mail,
)


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

    def test_mail_absent(self):
        self.assertIsNone(parse_mail(None))
        self.assertIsNone(parse_mail(""))
        self.assertIsNone(parse_mail("   "))

    def test_mail_valid(self):
        for value in (
            "bob@example.com",
            "BOB@EXAMPLE.COM",
            "a.b+tag@sub.example.co.uk",
            "weird!#$%&'*+/=?^_`{|}~-@example.com",
            "bob@x-1.example.museum",
            "bob@x.7",  # no TLD plausibility check
        ):
            self.assertEqual(parse_mail(value), value)

    def test_mail_stripped(self):
        self.assertEqual(parse_mail("  bob@example.com\n"), "bob@example.com")

    def test_mail_invalid(self):
        for value in (
            "bob",
            "bob@localhost",  # domain needs a dot
            "bob@@example.com",
            "bob@.com",
            "bob@-x.com",
            "bob@x-.com",
            "@example.com",
            "a..b@example.com",
            "a b@example.com",
            '"a b"@example.com',  # quoted local parts unsupported
            "bob@[192.0.2.1]",  # IP literals unsupported
            "josé@example.com",  # non-ASCII unsupported
            "bob@example.com\r\nX-Evil: 1",
            "bob@example.com\x00",
        ):
            with self.assertRaises(ValueError, msg=value):
                parse_mail(value)

    def test_mail_too_long(self):
        domain = "@example.com"
        local = "a" * (MAIL_MAX_LENGTH - len(domain))
        self.assertEqual(parse_mail(local + domain), local + domain)

        with self.assertRaises(ValueError):
            parse_mail("a" + local + domain)

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
