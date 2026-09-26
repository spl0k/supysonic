# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
from unittest.mock import patch

from supysonic.config import Config
from supysonic.scrobblers import Scrobbler, load_scrobblers
from supysonic.scrobblers.exceptions import ScrobblerImportError

from . import fakes
from .fakes import FakeScrobbler

FAKE = fakes.__name__


def _config(*scrobblers):
    return Config({"webapp": {"scrobblers": " ".join(scrobblers)}})


class LoadingTestCase(unittest.TestCase):
    def test_nothing_configured(self):
        self.assertEqual(load_scrobblers(_config()), [])

    def test_dotted_path(self):
        # Anything holding a dot is imported as-is, which is how an out-of-tree
        # scrobbler is loaded
        (scrobbler,) = load_scrobblers(_config(FAKE))

        self.assertIsInstance(scrobbler, FakeScrobbler)
        self.assertIsInstance(scrobbler, Scrobbler)

    def test_bare_name(self):
        # A bare name is one of the scrobblers shipped with Supysonic, so it's
        # looked up in their package rather than imported as a top-level module
        with patch("supysonic.scrobblers.import_module", return_value=fakes) as (
            import_module
        ):
            load_scrobblers(_config("whatever"))

        import_module.assert_called_once_with("supysonic.scrobblers.whatever")

    def test_config_is_passed_along(self):
        # A scrobbler gets the whole config, to read its own section out of it
        config = _config(FAKE)
        (scrobbler,) = load_scrobblers(config)

        self.assertIs(scrobbler.config, config)

    def test_several(self):
        # Loaded in the order they're listed, and a scrobbler can be listed
        # twice without the two instances interfering
        first, second = load_scrobblers(_config(FAKE, FAKE))

        self.assertIsNot(first, second)

    def test_unknown_module(self):
        with self.assertRaises(ScrobblerImportError) as cm:
            load_scrobblers(_config("tests.scrobblers.nosuchthing"))

        self.assertIn("nosuchthing", str(cm.exception))

    def test_module_declaring_no_scrobbler(self):
        with self.assertRaises(ScrobblerImportError) as cm:
            load_scrobblers(_config("tests.scrobblers.nothing"))

        self.assertIn("SCROBBLER", str(cm.exception))

    def test_scrobbler_of_the_wrong_type(self):
        with self.assertRaises(ScrobblerImportError) as cm:
            load_scrobblers(_config("tests.scrobblers.notascrobbler"))

        self.assertIn("Scrobbler", str(cm.exception))

    def test_unconfigured_is_reported(self):
        # Being listed but unusable is silent otherwise: every report would be
        # dropped without a word
        with patch.object(FakeScrobbler, "configured", False):
            with self.assertLogs("supysonic.scrobblers", "WARNING") as logs:
                (scrobbler,) = load_scrobblers(_config(FAKE))

            self.assertFalse(scrobbler.enabled)

        self.assertIn(FAKE, logs.output[0])

    def test_configured_is_silent(self):
        with self.assertNoLogs("supysonic.scrobblers", "WARNING"):
            load_scrobblers(_config(FAKE))


if __name__ == "__main__":
    unittest.main()
