# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Unit-level daemon tests — no real socket, engine, or blocking accept loop."""

import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch
from uuid import uuid4

import supysonic.daemon as daemon_pkg
from supysonic.daemon.client import DaemonClient
from supysonic.daemon.commands import (
    AddWatchedFolderCommand,
    DaemonCommand,
    JukeboxCommand,
    JukeboxResult,
    RemoveWatchedFolder,
    ScannerProgressCommand,
    ScannerProgressResult,
    ScannerStartCommand,
    StopCommand,
    decode,
    encode,
)
from supysonic.daemon.exceptions import (
    DaemonUnavailableError,
    UnknownCommandError,
)
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
        connection.send_bytes.assert_called_once()
        (raw,), _ = connection.send_bytes.call_args
        result = decode(raw)
        self.assertIsInstance(result, JukeboxResult)
        self.assertEqual(result.index, -1)

    def test_jukebox_command_actions(self):
        daemon = Mock()  # daemon.jukebox is a truthy Mock
        # Concrete (JSON-serializable) status so the encoded reply doesn't choke
        # on Mock attributes.
        daemon.jukebox.configure_mock(
            playing=False, index=0, gain=1.0, position=0, playlist=[]
        )
        connection = Mock()
        # Avoid touching the DB in the set/add-oriented connection handling
        with (
            patch("supysonic.daemon.commands.open_connection", return_value=False),
            patch("supysonic.daemon.commands.close_connection"),
        ):
            JukeboxCommand("start", ()).apply(connection, daemon)
            daemon.jukebox.start.assert_called_once_with()

            JukeboxCommand("stop", ()).apply(connection, daemon)
            daemon.jukebox.stop.assert_called_once_with()

    def test_jukebox_result_defaults(self):
        rv = JukeboxResult.from_jukebox(None)
        self.assertFalse(rv.playing)
        self.assertEqual(rv.index, -1)
        self.assertEqual(rv.gain, 1.0)
        self.assertEqual(rv.position, 0)
        self.assertEqual(rv.playlist, [])

    def test_jukebox_result_from_jukebox(self):
        jukebox = Mock(playing=True, index=2, gain=0.5, position=42)
        rv = JukeboxResult.from_jukebox(jukebox, ["/a.mp3", "/b.mp3"])
        self.assertTrue(rv.playing)
        self.assertEqual(rv.index, 2)
        self.assertEqual(rv.gain, 0.5)
        self.assertEqual(rv.position, 42)
        self.assertEqual(rv.playlist, ["/a.mp3", "/b.mp3"])

    def test_codec_round_trip(self):
        tid = uuid4()
        for msg in (
            AddWatchedFolderCommand("/music"),
            RemoveWatchedFolder("/music"),
            ScannerProgressCommand(),
            ScannerStartCommand(["Music"], True),
            StopCommand(),
            ScannerProgressResult(7),
            ScannerProgressResult(None),
            JukeboxResult.from_jukebox(None),
        ):
            self.assertEqual(decode(encode(msg)), msg)

        # UUID args aren't JSON-native: they survive as their canonical string.
        cmd = decode(encode(JukeboxCommand("add", [tid])))
        self.assertEqual(cmd.action, "add")
        self.assertEqual(cmd.args, [str(tid)])

    def test_decode_unknown_command(self):
        self.assertRaises(UnknownCommandError, decode, b'{"type": "bogus"}')

    def test_decode_malformed_payload(self):
        self.assertRaises(json.JSONDecodeError, decode, b"not json")

    def test_stop_command_is_noop(self):
        daemon = Mock()
        connection = Mock()
        StopCommand().apply(connection, daemon)
        connection.send_bytes.assert_not_called()
        daemon.assert_not_called()


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
        with patch.object(
            self.client, "_DaemonClient__get_connection", return_value=cm
        ):
            yield conn

    def test_add_remove_watched_folder_send(self):
        with self.__fake_connection() as conn:
            self.client.add_watched_folder("/music")
            conn.send_bytes.assert_called_once()
            sent = decode(conn.send_bytes.call_args[0][0])
            self.assertIsInstance(sent, AddWatchedFolderCommand)
            self.assertEqual(sent.folder, "/music")

        with self.__fake_connection() as conn:
            self.client.remove_watched_folder("/music")
            conn.send_bytes.assert_called_once()
            sent = decode(conn.send_bytes.call_args[0][0])
            self.assertIsInstance(sent, RemoveWatchedFolder)
            self.assertEqual(sent.folder, "/music")


class DaemonServerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = TestConfig(False, False)
        self.daemon = Daemon(self.config)

    def test_handle_unknown_command(self):
        # An unregistered command tag is logged and ignored. assertLogs both
        # verifies the warning and captures it (keeping it off the console).
        conn = Mock()
        conn.recv_bytes.return_value = b'{"type": "bogus"}'
        # name-mangled private method
        with self.assertLogs("supysonic.daemon.server", level="WARNING"):
            self.daemon._Daemon__handle_connection(conn)
        conn.recv_bytes.assert_called_once()

    def test_handle_malformed_payload(self):
        # A non-JSON payload is logged and ignored, not executed.
        conn = Mock()
        conn.recv_bytes.return_value = b"not json"
        with self.assertLogs("supysonic.daemon.server", level="WARNING"):
            self.daemon._Daemon__handle_connection(conn)
        conn.recv_bytes.assert_called_once()

    def test_handle_stop_command(self):
        # A StopCommand is dispatched and no-ops (no reply, no crash).
        conn = Mock()
        conn.recv_bytes.return_value = encode(StopCommand())
        self.daemon._Daemon__handle_connection(conn)
        conn.send_bytes.assert_not_called()

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
