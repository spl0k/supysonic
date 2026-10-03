# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
from unittest.mock import patch

from supysonic.config import Config
from supysonic.lyrics import LyricsProvider, load_lyrics_providers
from supysonic.lyrics.exceptions import LyricsProviderImportError

from . import fakes, silent
from .fakes import FakeProvider

FAKE = fakes.__name__
SILENT = silent.__name__


def _config(*providers):
    return Config({"webapp": {"lyrics_providers": " ".join(providers)}})


class LoadingTestCase(unittest.TestCase):
    def test_nothing_configured(self):
        self.assertEqual(load_lyrics_providers(_config()), [])

    def test_dotted_path(self):
        (provider,) = load_lyrics_providers(_config(FAKE))

        self.assertIsInstance(provider, FakeProvider)
        self.assertIsInstance(provider, LyricsProvider)

    def test_bare_name(self):
        # A bare name is one of the providers shipped with Supysonic
        with patch("supysonic.extensions.import_module", return_value=fakes) as (
            import_module
        ):
            load_lyrics_providers(_config("whatever"))

        import_module.assert_called_once_with("supysonic.lyrics.whatever")

    def test_config_is_passed_along(self):
        config = _config(FAKE)
        (provider,) = load_lyrics_providers(config)

        self.assertIs(provider.config, config)

    def test_order_is_kept(self):
        # It's the order they're asked in
        providers = load_lyrics_providers(_config(SILENT, FAKE))

        self.assertEqual([p.name for p in providers], ["silent", "fake"])

    def test_unknown_module(self):
        with self.assertRaises(LyricsProviderImportError) as cm:
            load_lyrics_providers(_config("tests.lyrics.nosuchthing"))

        self.assertIn("nosuchthing", str(cm.exception))

    def test_module_declaring_no_provider(self):
        with self.assertRaises(LyricsProviderImportError) as cm:
            load_lyrics_providers(_config("tests.lyrics.nothing"))

        self.assertIn("PROVIDER", str(cm.exception))

    def test_provider_of_the_wrong_type(self):
        with self.assertRaises(LyricsProviderImportError) as cm:
            load_lyrics_providers(_config("tests.lyrics.notaprovider"))

        self.assertIn("LyricsProvider", str(cm.exception))

    def test_unconfigured_is_skipped(self):
        with patch.object(FakeProvider, "configured", False):
            with self.assertLogs("supysonic.lyrics", "WARNING") as logs:
                providers = load_lyrics_providers(_config(FAKE, SILENT))

        self.assertEqual([p.name for p in providers], ["silent"])
        self.assertIn(FAKE, logs.output[0])

    def test_configured_is_silent(self):
        with self.assertNoLogs("supysonic.lyrics", "WARNING"):
            load_lyrics_providers(_config(FAKE))


if __name__ == "__main__":
    unittest.main()
