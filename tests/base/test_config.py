# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import tempfile
import unittest
from unittest.mock import patch

from supysonic.config import (
    Config,
    MappingSection,
    Option,
    Section,
    TranscodingSection,
    WebappSection,
)
from supysonic.parsers import parse_bool, parse_int


class SampleSection(Section, section="unknown"):
    """A section of the sample file no core code knows about, standing in for
    one a pluggable module would declare."""

    int = Option(0, parse_int)
    yn_true = Option(False, parse_bool)
    string = Option("nothing")


class Issue84Section(Section, section="issue84"):
    variable = Option()
    key = Option()


class SampleMappingSection(MappingSection, section="samplemapping"):
    """Stands in for a mapping section a pluggable module would declare.

    Merely declaring it guards against the section keyword clashing with a
    parameter of ``ABCMeta.__new__``, which ``MappingSection`` goes through.
    """


class ConfigTestCase(unittest.TestCase):
    def __write_config(self, contents):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".ini", delete=False, encoding="utf-8"
        ) as f:
            f.write(contents)
            path = f.name
        self.addCleanup(os.remove, path)
        return path

    # Defaults

    def test_defaults(self):
        # A config built without a file holds every declared default
        conf = Config()

        self.assertEqual(conf.webapp.cache_size, 512)
        self.assertIs(conf.webapp.mount_api, True)
        self.assertIs(conf.base.follow_symlinks, False)
        self.assertEqual(conf.base.scanner_extensions, ())
        self.assertEqual(conf.webapp.log_level, "WARNING")
        self.assertIsNone(conf.lastfm.api_key)

    def test_http_error_status_defaults_off(self):
        # Opt-in only: enabling it by default would break clients that treat any
        # non-2xx response as a connection failure
        self.assertIs(Config().webapp.use_http_error_status, False)
        self.assertIs(
            Config.from_ini("tests/assets/sample.ini").webapp.use_http_error_status,
            False,
        )

    def test_partial_section_keeps_other_defaults(self):
        # A section of the file only overrides the options it lists
        path = self.__write_config("[base]\nscanner_extensions = mp3 flac\n")
        conf = Config.from_ini(path)

        self.assertEqual(conf.base.scanner_extensions, ("mp3", "flac"))
        self.assertEqual(conf.base.follow_symlinks, False)

        # ... and only for that config, defaults being declared on the class
        self.assertEqual(Config().base.scanner_extensions, ())

    # Sections are objects

    def test_sections_are_frozen(self):
        conf = Config()

        with self.assertRaises(AttributeError):
            conf.webapp.cache_size = 1024
        self.assertEqual(conf.webapp.cache_size, 512)

    def test_unknown_option_raises(self):
        conf = Config()

        with self.assertRaises(AttributeError):
            conf.webapp.cache_sise
        with self.assertRaises(AttributeError):
            conf.webapp.cache_sise = 1024

    def test_unknown_key_is_ignored(self):
        # A leftover or mistyped key doesn't become a value and doesn't break
        # the startup either
        path = self.__write_config("[webapp]\ncahce_size = 1024\n")
        conf = Config.from_ini(path)

        self.assertEqual(conf.webapp.cache_size, 512)
        self.assertFalse(hasattr(conf.webapp, "cahce_size"))

    def test_override(self):
        # The one way to alter a built config, leaving the original alone
        conf = Config()
        section = conf.webapp

        conf.override(WebappSection, cache_size=1024)

        self.assertEqual(conf.webapp.cache_size, 1024)
        self.assertIsNot(conf.webapp, section)
        self.assertEqual(section.cache_size, 512)
        # Other values of the section are carried over
        self.assertIs(conf.webapp.mount_api, True)

    def test_same_instance_returned(self):
        conf = Config()
        self.assertIs(conf.webapp, conf.webapp)

    def test_option_reachable_on_the_class(self):
        # Reading an option off the class gives the declaration itself, so a
        # default can be looked up without building a config
        option = WebappSection.cache_size

        self.assertIsInstance(option, Option)
        self.assertEqual(option.default, 512)

    def test_repr(self):
        self.assertEqual(
            repr(Config().listenbrainz),
            "ListenBrainzSection(api_url='https://api.listenbrainz.org')",
        )

    # Parsing

    def test_typed_keys(self):
        path = self.__write_config(
            "[base]\nfollow_symlinks = yes\n"
            "[webapp]\ncache_size = 512\ntranscode_cache_size = 1024\n"
            "mount_api = off\nmount_webui = 1\nlog_rotate = no\n"
            "use_http_error_status = on\n"
            "[daemon]\nrun_watcher = true\nwait_delay = 0.5\n"
        )
        conf = Config.from_ini(path)

        self.assertIs(conf.base.follow_symlinks, True)
        self.assertEqual(conf.webapp.cache_size, 512)
        self.assertEqual(conf.webapp.transcode_cache_size, 1024)
        self.assertIs(conf.webapp.mount_api, False)
        self.assertIs(conf.webapp.mount_webui, True)
        self.assertIs(conf.webapp.log_rotate, False)
        self.assertIs(conf.webapp.use_http_error_status, True)
        self.assertIs(conf.daemon.run_watcher, True)
        self.assertEqual(conf.daemon.wait_delay, 0.5)

    def test_string_keys_arent_coerced(self):
        # Regression: string values that look like numbers or booleans used to be
        # silently converted, breaking str operations on them
        path = self.__write_config(
            "[lastfm]\napi_key = 1234567890\nsecret = 0987654321\n"
            "[webapp]\nlog_level = 1\nindex_ignored_prefixes = 1 2 3\n"
            "[transcoding]\ndefault_transcode_target = 3\n"
            "[mimetypes]\nfoo = on\n"
        )
        conf = Config.from_ini(path)

        self.assertEqual(conf.lastfm.api_key, "1234567890")
        self.assertEqual(conf.lastfm.secret, "0987654321")
        self.assertEqual(conf.webapp.log_level, "1")
        self.assertEqual(conf.webapp.index_ignored_prefixes, "1 2 3")
        self.assertEqual(conf.transcoding.default_transcode_target, "3")
        self.assertEqual(conf.mimetypes["foo"], "on")

    def test_scanner_extensions(self):
        path = self.__write_config("[base]\nscanner_extensions = MP3 .flac\n")
        conf = Config.from_ini(path)

        # Lower-cased and stripped of their leading dot, ready for comparison
        self.assertEqual(conf.base.scanner_extensions, ("mp3", "flac"))

    def test_transcode_target_is_lowercased(self):
        path = self.__write_config("[transcoding]\ndefault_transcode_target = MP3\n")
        conf = Config.from_ini(path)

        self.assertEqual(conf.transcoding.default_transcode_target, "mp3")

    def test_invalid_typed_value(self):
        for section, option in (
            ("webapp", "cache_size = lots"),
            ("webapp", "cache_size = -1"),
            ("webapp", "use_http_error_status = sometimes"),
            ("daemon", "run_watcher = maybe"),
            ("daemon", "wait_delay = soon"),
            ("daemon", "wait_delay = nan"),
            # Ends up in a cache key, so it has to be a bare file extension
            ("transcoding", "default_transcode_target = ../evil"),
            ("transcoding", "default_transcode_target = sub/dir"),
            ("transcoding", "default_transcode_target = .mp3"),
            ("transcoding", "default_transcode_target = toolongformat"),
            ("transcoding", "default_transcode_target ="),
        ):
            path = self.__write_config(f"[{section}]\n{option}\n")
            key = option.split(" ", 1)[0]
            with self.subTest(option=option):
                # Core sections are built eagerly, so a bad value is reported
                # when the config is read rather than on first use
                with self.assertRaises(ValueError) as cm:
                    Config.from_ini(path)
                self.assertIn(f"{section}.{key}", str(cm.exception))

    def test_no_interpolation(self):
        conf = Config.from_ini("tests/assets/sample.ini")
        section = conf.section(Issue84Section)

        self.assertEqual(section.variable, "value")
        self.assertEqual(section.key, "some value with a %variable")

    # Mapping sections

    def test_mapping_section(self):
        path = self.__write_config("[mimetypes]\nmp3 = audio/mpeg\nogg = audio/ogg\n")
        conf = Config.from_ini(path)

        self.assertIsInstance(conf.mimetypes, MappingSection)
        self.assertEqual(
            dict(conf.mimetypes), {"mp3": "audio/mpeg", "ogg": "audio/ogg"}
        )
        self.assertEqual(conf.mimetypes["mp3"], "audio/mpeg")
        self.assertIn("ogg", conf.mimetypes)
        self.assertIsNone(conf.mimetypes.get("flac"))
        self.assertEqual(len(conf.mimetypes), 2)

        # Nothing configured is an empty mapping, not an error
        self.assertEqual(len(Config().mimetypes), 0)

    def test_declared_mapping_section(self):
        path = self.__write_config("[samplemapping]\nsome = value\n")
        section = Config.from_ini(path).section(SampleMappingSection)

        self.assertIsInstance(section, MappingSection)
        self.assertEqual(dict(section), {"some": "value"})

    # Transcoding, the free-form section

    def __transcoding(self, **raw):
        return Config({"transcoding": raw}).transcoding

    def test_transcoding_specific_transcoder_wins(self):
        section = self.__transcoding(
            transcoder_mp3_ogg="specific",
            transcoder="generic",
            decoder="dec",
            encoder="enc",
        )
        self.assertEqual(section.resolve("mp3", "ogg"), ("specific", None, None))

    def test_transcoding_decoder_encoder_pair(self):
        section = self.__transcoding(
            decoder_mp3="dec mp3", encoder="enc", transcoder="generic"
        )
        self.assertEqual(section.resolve("mp3", "ogg"), (None, "dec mp3", "enc"))

        # Each side falls back to its bare key
        section = self.__transcoding(decoder="dec", encoder_ogg="enc ogg")
        self.assertEqual(section.resolve("mp3", "ogg"), (None, "dec", "enc ogg"))

    def test_transcoding_falls_back_to_generic_transcoder(self):
        # Half a pipeline is no pipeline
        section = self.__transcoding(decoder_mp3="dec", transcoder="generic")
        self.assertEqual(section.resolve("mp3", "ogg"), ("generic", None, None))

    def test_transcoding_impossible(self):
        self.assertEqual(self.__transcoding().resolve("mp3", "ogg"), (None, None, None))
        self.assertEqual(
            self.__transcoding(encoder_ogg="enc").resolve("mp3", "ogg"),
            (None, None, None),
        )

    # Sections declared elsewhere

    def test_section_of_an_undeclared_section(self):
        # Sections of the file that no core section declares are kept around, so
        # a module loaded later on can still read its own configuration
        conf = Config.from_ini("tests/assets/sample.ini")
        section = conf.section(SampleSection)

        self.assertEqual(section.int, 42)
        self.assertIs(section.yn_true, True)
        self.assertEqual(section.string, "Some text here")

    def test_section_is_cached(self):
        conf = Config.from_ini("tests/assets/sample.ini")
        self.assertIs(conf.section(SampleSection), conf.section(SampleSection))

    def test_section_absent_from_the_file(self):
        section = Config().section(SampleSection)

        self.assertEqual(section.int, 0)
        self.assertIs(section.yn_true, False)
        self.assertEqual(section.string, "nothing")

    def test_mixin_contributes_its_options(self):
        # LoggingOptions is shared by WEBAPP and DAEMON
        for section in (Config().webapp, Config().daemon):
            with self.subTest(section=type(section).__name__):
                self.assertIsNone(section.log_file)
                self.assertEqual(section.log_level, "WARNING")
                self.assertIs(section.log_rotate, True)

    def test_from_common_locations(self):
        path = self.__write_config("[webapp]\ncache_size = 7\n")
        with patch.object(Config, "common_paths", [path]):
            self.assertEqual(Config.from_common_locations().webapp.cache_size, 7)

    def test_section_name_is_case_insensitive(self):
        path = self.__write_config("[WebApp]\ncache_size = 42\n")
        self.assertEqual(Config.from_ini(path).webapp.cache_size, 42)

    def test_transcoding_section_is_the_declared_one(self):
        self.assertIsInstance(Config().transcoding, TranscodingSection)


if __name__ == "__main__":
    unittest.main()
