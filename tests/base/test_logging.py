# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os
import tempfile
import unittest
from logging.handlers import TimedRotatingFileHandler

from supysonic.logs import logger, setup_logging

FILE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
STREAM_FORMAT = "[%(levelname)s] %(message)s"


class LoggingTestCase(unittest.TestCase):
    def setUp(self):
        self.__handlers = list(logger.handlers)
        self.__level = logger.level

        self.__tempdir = tempfile.TemporaryDirectory()
        self.logfile = os.path.join(self.__tempdir.name, "supysonic.log")

    def tearDown(self):
        # Close whatever setup_logging installed before the temp dir goes away,
        # or removing it fails on Windows
        for handler in self.added_handlers:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(self.__level)
        self.__tempdir.cleanup()

    @property
    def added_handlers(self):
        return [h for h in logger.handlers if h not in self.__handlers]

    def assertSingleHandler(self, cls):
        handlers = self.added_handlers
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], cls)
        return handlers[0]

    def test_no_file_no_fallback(self):
        # The web app doesn't log anywhere when no log file is set. Several test
        # modules rely on the 'supysonic' logger staying handler-less, silencing
        # their own child logger with a NullHandler.
        setup_logging({"log_file": None})
        self.assertEqual(self.added_handlers, [])

    def test_no_file_fallback_to_stderr(self):
        setup_logging({"log_file": None}, fallback_to_stderr=True)
        handler = self.assertSingleHandler(logging.StreamHandler)
        self.assertEqual(handler.formatter._fmt, STREAM_FORMAT)

    def test_file(self):
        setup_logging({"log_file": self.logfile, "log_rotate": False})
        handler = self.assertSingleHandler(logging.FileHandler)
        self.assertNotIsInstance(handler, TimedRotatingFileHandler)
        self.assertEqual(handler.baseFilename, self.logfile)
        self.assertEqual(handler.formatter._fmt, FILE_FORMAT)

    def test_file_rotating(self):
        setup_logging({"log_file": self.logfile, "log_rotate": True})
        handler = self.assertSingleHandler(TimedRotatingFileHandler)
        self.assertEqual(handler.when, "MIDNIGHT")
        self.assertEqual(handler.baseFilename, self.logfile)
        self.assertEqual(handler.formatter._fmt, FILE_FORMAT)

    def test_file_wins_over_fallback(self):
        setup_logging({"log_file": self.logfile}, fallback_to_stderr=True)
        self.assertSingleHandler(logging.FileHandler)

    def test_empty_config(self):
        setup_logging({})
        self.assertEqual(self.added_handlers, [])
        self.assertEqual(logger.level, self.__level)

    def test_idempotent(self):
        setup_logging({"log_file": self.logfile})
        first = self.assertSingleHandler(logging.FileHandler)

        setup_logging({"log_file": self.logfile})
        second = self.assertSingleHandler(logging.FileHandler)

        self.assertIsNot(second, first)
        self.assertIsNone(first.stream)

    def test_level(self):
        for value in ("DEBUG", "debug"):
            with self.subTest(value=value):
                setup_logging({"log_file": None, "log_level": value})
                self.assertEqual(logger.level, logging.DEBUG)

    def test_level_unset(self):
        for config in ({"log_file": None}, {"log_file": None, "log_level": ""}):
            with self.subTest(config=config):
                logger.setLevel(logging.ERROR)
                setup_logging(config)
                self.assertEqual(logger.level, logging.ERROR)

    def test_level_unknown(self):
        # 'raiseexceptions' used to resolve to the logging module attribute,
        # True == 1, silently enabling full debug logging
        for value in ("nonsense", "1", "raiseexceptions"):
            with self.subTest(value=value):
                logger.setLevel(logging.CRITICAL)
                with self.assertLogs(logger, logging.WARNING) as cm:
                    setup_logging({"log_file": None, "log_level": value})
                    # assertLogs restores the level on exit, so check inside
                    self.assertEqual(logger.level, logging.NOTSET)
                self.assertIn(repr(value), cm.output[0])


if __name__ == "__main__":
    unittest.main()
