# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import shlex
import shutil
import tempfile
import unittest
from contextlib import contextmanager

from click.testing import CliRunner

from supysonic.cli import cli
from supysonic.config import BaseSection
from supysonic.db.connection import init_database, release_database
from supysonic.db.models import Folder, Track, User
from supysonic.managers.user import UserManager

from ..testbase import TestConfig, get_test_db_uri, teardown_test_db

SILENCE_MP3 = os.path.join("tests", "assets", "folder", "silence.mp3")


class CLITestCase(unittest.TestCase):
    """Exercises the CLI end to end, asserting the effect of each command on the
    database and on the messages it prints."""

    def setUp(self):
        self.__uri, self.__db = get_test_db_uri()
        self.__conf = TestConfig(False, False, base={"database_uri": self.__uri})

        self.__runner = CliRunner()

    def tearDown(self):
        teardown_test_db(self.__db)

    def __invoke(self, cmd, expect_fail=False):
        rv = self.__runner.invoke(
            cli, shlex.split(cmd), catch_exceptions=expect_fail, obj=self.__conf
        )
        func = self.assertNotEqual if expect_fail else self.assertEqual
        func(rv.exit_code, 0)
        return rv

    @contextmanager
    def __rebind(self):
        init_database(self.__uri)
        try:
            yield
        finally:
            release_database()

    def __add_folder(self, name, path, expect_fail=False):
        self.__invoke(f"folder add {name} {shlex.quote(path)}", expect_fail)

    def test_folder_add(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)

        with self.__rebind():
            f = Folder.select().first()
            self.assertIsNotNone(f)
            self.assertEqual(f.path, d)

    def test_folder_add_errors(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("f1", d)
            self.__add_folder("f2", d, True)
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("f1", d, True)
        self.__invoke("folder add f3 /invalid/path", True)

        with self.__rebind():
            self.assertEqual(Folder.select().count(), 1)

    def test_folder_delete(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
        self.__invoke("folder delete randomfolder", True)
        self.__invoke("folder delete tmpfolder")

        with self.__rebind():
            self.assertEqual(Folder.select().count(), 0)

    def test_folder_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
            rv = self.__invoke("folder list")
            self.assertIn("tmpfolder", rv.output)
            self.assertIn(d, rv.output)

    def test_folder_scan(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
            with tempfile.NamedTemporaryFile(dir=d) as tf:
                # The test config points the daemon at a socket nothing listens
                # on, so the automatic mode falls back to a foreground scan
                rv = self.__invoke("folder scan")
                self.assertIn("scanning in foreground", rv.output)
                self.assertIn("Scanning done", rv.output)
                self.assertIn("Added: 0 artists, 0 albums, 0 tracks", rv.output)
                self.assertIn("Deleted: 0 artists, 0 albums, 0 tracks", rv.output)
                # The lone file is visited but carries no readable tag, so it's
                # skipped rather than reported: stats.errors is only for field
                # validation and bad encodings
                self.assertIn("1 files scanned", rv.output)
                self.assertNotIn("Errors in:", rv.output)
                self.assertNotIn(os.path.basename(tf.name), rv.output)

                rv = self.__invoke("folder scan tmpfolder nonexistent")
                self.assertIn("No such folder(s): nonexistent", rv.output)
                self.assertNotIn("No such folder(s): tmpfolder", rv.output)

        with self.__rebind():
            self.assertEqual(Track.select().count(), 0)

    def test_folder_scan_extensions(self):
        # A configured extension whitelist is parsed into a tuple, then consulted
        # for every file found: only whitelisted ones get scanned
        self.__conf.override(BaseSection, scanner_extensions="mp3 flac")
        with tempfile.TemporaryDirectory() as d:
            shutil.copyfile(SILENCE_MP3, os.path.join(d, "silence.mp3"))
            shutil.copyfile(SILENCE_MP3, os.path.join(d, "silence.ogg"))
            self.__add_folder("tmpfolder", d)
            self.__invoke("folder scan")

        with self.__rebind():
            paths = [t.path for t in Track.select()]
            self.assertEqual(len(paths), 1)
            self.assertTrue(paths[0].endswith("silence.mp3"))

    def test_user_add(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user add -p alice alice", True)

        with self.__rebind():
            self.assertEqual(User.select().count(), 1)

    def test_user_add_mail(self):
        self.__invoke("user add -p Alic3 -e lolnope alice", True)
        with self.__rebind():
            self.assertEqual(User.select().count(), 0)

        self.__invoke("user add -p Alic3 -e alice@example.com alice")
        with self.__rebind():
            self.assertEqual(User.get(name="alice").mail, "alice@example.com")

        # not providing an address leaves it unset
        self.__invoke("user add -p B0b bob")
        with self.__rebind():
            self.assertIsNone(User.get(name="bob").mail)

    def test_user_delete(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user delete alice")
        self.__invoke("user delete bob", True)

        with self.__rebind():
            self.assertEqual(User.select().count(), 0)

    def test_user_list(self):
        self.__invoke("user add -p Alic3 alice")
        rv = self.__invoke("user list")
        self.assertIn("alice", rv.output)

    def test_user_setadmin(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user setroles -A alice")
        self.__invoke("user setroles -A bob", True)
        with self.__rebind():
            self.assertTrue(User.get(name="alice").admin)

    def test_user_unsetadmin(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user setroles -A alice")
        self.__invoke("user setroles -a alice")
        with self.__rebind():
            self.assertFalse(User.get(name="alice").admin)

    def test_user_setjukebox(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user setroles -J alice")
        with self.__rebind():
            self.assertTrue(User.get(name="alice").jukebox)

    def test_user_unsetjukebox(self):
        self.__invoke("user add -p Alic3 alice")
        self.__invoke("user setroles -J alice")
        self.__invoke("user setroles -j alice")
        with self.__rebind():
            self.assertFalse(User.get(name="alice").jukebox)

    def test_user_changepass(self):
        self.__invoke("user add -p Alic3 alice")

        rv = self.__invoke("user changepass alice -p newpass")
        self.assertIn("Successfully changed 'alice' password", rv.output)
        with self.__rebind():
            manager = UserManager()
            self.assertIsNotNone(manager.try_auth("alice", "newpass"))
            self.assertIsNone(manager.try_auth("alice", "Alic3"))

        rv = self.__invoke("user changepass bob -p B0b", True)
        self.assertIn("User 'bob' does not exist.", rv.output)

    def test_user_rename(self):
        self.__invoke("user add -p Alic3 alice")

        # Renaming to the same name returns early, without echoing anything
        rv = self.__invoke("user rename alice alice")
        self.assertNotIn("renamed to", rv.output)
        with self.__rebind():
            self.assertEqual(User.select().count(), 1)
            self.assertEqual(User.select().first().name, "alice")

        self.__invoke("user rename bob charles", True)

        self.__invoke("user rename alice ''", True)
        with self.__rebind():
            self.assertEqual(User.select().first().name, "alice")

        self.__invoke("user rename alice bob")
        with self.__rebind():
            self.assertEqual(User.select().first().name, "bob")

        self.__invoke("user add -p Ch4rl3s charles")
        self.__invoke("user rename bob charles", True)
        with self.__rebind():
            self.assertEqual(User.select().where(User.name == "bob").count(), 1)
            self.assertEqual(User.select().where(User.name == "charles").count(), 1)


if __name__ == "__main__":
    unittest.main()
