# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Unit-level daemon tests — no real socket, engine, or blocking accept loop."""

import os
import tempfile
import unittest

from contextlib import contextmanager
from unittest.mock import Mock, patch

import supysonic.daemon as daemon_pkg

from supysonic.daemon.client import (
    AddWatchedFolderCommand,
    DaemonClient,
    DaemonCommand,
    JukeboxCommand,
    JukeboxResult,
    RemoveWatchedFolder,
)
from supysonic.daemon.exceptions import DaemonUnavailableError
from supysonic.daemon.server import Daemon
from supysonic.db import init_database, release_database

from ..testbase import TestConfig


class DaemonCommandTestCase(unittest.TestCase):
    def test_base_command_not_implemented(self):
        self.assertRaises(NotImplementedError, DaemonCommand().apply, None, None)

    def test_watched_folder_commands(self):
        daemon = Mock()  # daemon.watcher is a truthy Mock
        AddWatchedFolderCommand("/music").apply(Mock(), daemon)
        daemon.watcher.add_folder.assert_called_once_with("/music")

        RemoveWatchedFolder("/music").apply(Mock(), daemon)
        daemon.watcher.remove_folder.assert_called_once_with("/music")

    def test_jukebox_command_no_jukebox(self):
        # With no jukebox configured, a default (empty) result is sent back.
        daemon = Mock(jukebox=None)
        connection = Mock()
        JukeboxCommand("get", ()).apply(connection, daemon)
        connection.send.assert_called_once()
        (result,), _ = connection.send.call_args
        self.assertIsInstance(result, JukeboxResult)
        self.assertEqual(result.index, -1)

    def test_jukebox_command_actions(self):
        daemon = Mock()  # daemon.jukebox is a truthy Mock
        connection = Mock()
        # Avoid touching the DB in the set/add-oriented connection handling
        with patch("supysonic.daemon.client.open_connection", return_value=False), patch(
            "supysonic.daemon.client.close_connection"
        ):
            JukeboxCommand("start", ()).apply(connection, daemon)
            daemon.jukebox.start.assert_called_once_with()

            JukeboxCommand("stop", ()).apply(connection, daemon)
            daemon.jukebox.stop.assert_called_once_with()

    def test_jukebox_result_defaults(self):
        rv = JukeboxResult(None)
        self.assertFalse(rv.playing)
        self.assertEqual(rv.index, -1)
        self.assertEqual(rv.gain, 1.0)
        self.assertEqual(rv.position, 0)
        self.assertEqual(rv.playlist, ())


class DaemonClientTestCase(unittest.TestCase):
    def setUp(self):
        # DaemonClient reads the daemon secret key from the DB (Meta table)
        init_database("sqlite:")
        self.addCleanup(release_database)
        self.client = DaemonClient(address="dummy-supysonic-daemon-address")

    def test_no_address_raises(self):
        object.__setattr__(self.client, "_DaemonClient__address", "")
        self.assertRaises(DaemonUnavailableError, self.client.scan)

    def test_type_errors(self):
        self.assertRaises(TypeError, self.client.add_watched_folder, 1)
        self.assertRaises(TypeError, self.client.remove_watched_folder, 1)
        self.assertRaises(TypeError, self.client.scan, "not a list")
        self.assertRaises(TypeError, self.client.jukebox_control, 1)

    @contextmanager
    def __fake_connection(self):
        conn = Mock()
        cm = Mock()
        cm.__enter__ = Mock(return_value=conn)
        cm.__exit__ = Mock(return_value=False)
        with patch.object(self.client, "_DaemonClient__get_connection", return_value=cm):
            yield conn

    def test_add_remove_watched_folder_send(self):
        with self.__fake_connection() as conn:
            self.client.add_watched_folder("/music")
            conn.send.assert_called_once()
            self.assertIsInstance(conn.send.call_args[0][0], AddWatchedFolderCommand)

        with self.__fake_connection() as conn:
            self.client.remove_watched_folder("/music")
            conn.send.assert_called_once()
            self.assertIsInstance(conn.send.call_args[0][0], RemoveWatchedFolder)


class DaemonServerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = TestConfig(False, False)
        self.daemon = Daemon(self.config)

    def test_handle_unknown_command(self):
        # A payload that isn't a DaemonCommand is logged and ignored. assertLogs
        # both verifies the warning and captures it (keeping it off the console).
        conn = Mock()
        conn.recv.return_value = "not a command"
        # name-mangled private method
        with self.assertLogs("supysonic.daemon.server", level="WARNING"):
            self.daemon._Daemon__handle_connection(conn)
        conn.recv.assert_called_once()

    def test_start_scan_already_running(self):
        scanner = Mock()
        scanner.is_alive.return_value = True
        object.__setattr__(self.daemon, "_Daemon__scanner", scanner)

        self.daemon.start_scan(folders=["Music"])
        scanner.queue_folder.assert_called_once_with("Music")

    def test_start_scan_parses_extensions(self):
        self.config.BASE["scanner_extensions"] = "mp3 flac"
        with patch("supysonic.daemon.server.Scanner") as ScannerMock:
            self.daemon.start_scan(folders=["Music"])
            _, kwargs = ScannerMock.call_args
            self.assertEqual(kwargs["extensions"], ["mp3", "flac"])
            ScannerMock.return_value.start.assert_called_once()


class DaemonSetupTestCase(unittest.TestCase):
    def setUp(self):
        self.__handlers = list(daemon_pkg.logger.handlers)
        self.__level = daemon_pkg.logger.level

    def tearDown(self):
        for h in list(daemon_pkg.logger.handlers):
            if h not in self.__handlers:
                daemon_pkg.logger.removeHandler(h)
                h.close()
        daemon_pkg.logger.setLevel(self.__level)
        daemon_pkg.daemon = None

    def test_setup_logging_stream(self):
        daemon_pkg.setup_logging({"log_file": None})

    def test_setup_logging_file(self):
        with tempfile.TemporaryDirectory() as d:
            daemon_pkg.setup_logging(
                {
                    "log_file": os.path.join(d, "s.log"),
                    "log_rotate": False,
                    "log_level": "DEBUG",
                }
            )
            for h in list(daemon_pkg.logger.handlers):
                if h not in self.__handlers:
                    daemon_pkg.logger.removeHandler(h)
                    h.close()

    def test_setup_logging_rotating(self):
        with tempfile.TemporaryDirectory() as d:
            daemon_pkg.setup_logging(
                {"log_file": os.path.join(d, "s.log"), "log_rotate": True}
            )
            for h in list(daemon_pkg.logger.handlers):
                if h not in self.__handlers:
                    daemon_pkg.logger.removeHandler(h)
                    h.close()

    def test_terminate_signal_handler(self):
        terminate = vars(daemon_pkg)["__terminate"]
        daemon_pkg.daemon = Mock()
        with patch("supysonic.daemon.release_database") as rel:
            terminate(15, None)
        daemon_pkg.daemon.terminate.assert_called_once_with()
        rel.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
