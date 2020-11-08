#!/usr/bin/env python
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import tempfile
import shlex
import unittest

from io import StringIO
from pony.orm import db_session

from supysonic.db import Folder, User, init_database, release_database
from supysonic.cli import SupysonicCLI

from ..testbase import TestConfig


class CLITestCase(unittest.TestCase):
    """ Really basic tests. Some even don't check anything but are just there for coverage """

    def setUp(self):
        conf = TestConfig(False, False)
        self.__db = tempfile.mkstemp()
        conf.BASE["database_uri"] = "sqlite:///" + self.__db[1]
        init_database(conf.BASE["database_uri"])

        self.__stdout = StringIO()
        self.__stderr = StringIO()
        self.__cli = SupysonicCLI(conf, stdout=self.__stdout, stderr=self.__stderr)

    def tearDown(self):
        self.__stdout.close()
        self.__stderr.close()
        release_database()
        os.close(self.__db[0])
        os.remove(self.__db[1])

    def __add_folder(self, name, path):
        self.__cli.onecmd("folder add {0} {1}".format(name, shlex.quote(path)))

    def test_folder_add(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)

        with db_session:
            f = Folder.select().first()
            self.assertIsNotNone(f)
            self.assertEqual(f.path, d)

    def test_folder_add_errors(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("f1", d)
            self.__add_folder("f2", d)
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("f1", d)
        self.__cli.onecmd("folder add f3 /invalid/path")

        with db_session:
            self.assertEqual(Folder.select().count(), 1)

    def test_folder_delete(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
        self.__cli.onecmd("folder delete randomfolder")
        self.__cli.onecmd("folder delete tmpfolder")

        with db_session:
            self.assertEqual(Folder.select().count(), 0)

    def test_folder_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
            self.__cli.onecmd("folder list")
            self.assertIn("tmpfolder", self.__stdout.getvalue())
            self.assertIn(d, self.__stdout.getvalue())

    def test_folder_scan(self):
        with tempfile.TemporaryDirectory() as d:
            self.__add_folder("tmpfolder", d)
            with tempfile.NamedTemporaryFile(dir=d):
                self.__cli.onecmd("folder scan")
                self.__cli.onecmd("folder scan tmpfolder nonexistent")

    def test_user_add(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user add -p alice alice")

        with db_session:
            self.assertEqual(User.select().count(), 1)

    def test_user_delete(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user delete alice")
        self.__cli.onecmd("user delete bob")

        with db_session:
            self.assertEqual(User.select().count(), 0)

    def test_user_list(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user list")
        self.assertIn("alice", self.__stdout.getvalue())

    def test_user_setadmin(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user setroles -A alice")
        self.__cli.onecmd("user setroles -A bob")
        with db_session:
            self.assertTrue(User.get(name="alice").admin)

    def test_user_unsetadmin(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user setroles -A alice")
        self.__cli.onecmd("user setroles -a alice")
        with db_session:
            self.assertFalse(User.get(name="alice").admin)

    def test_user_setjukebox(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user setroles -J alice")
        with db_session:
            self.assertTrue(User.get(name="alice").jukebox)

    def test_user_unsetjukebox(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user setroles -J alice")
        self.__cli.onecmd("user setroles -j alice")
        with db_session:
            self.assertFalse(User.get(name="alice").jukebox)

    def test_user_changepass(self):
        self.__cli.onecmd("user add -p Alic3 alice")
        self.__cli.onecmd("user changepass alice newpass")
        self.__cli.onecmd("user changepass bob B0b")

    def test_other(self):
        self.assertTrue(self.__cli.do_EOF(""))
        self.__cli.onecmd("unknown command")
        self.__cli.postloop()
        self.__cli.completedefault("user", "user", 4, 4)


if __name__ == "__main__":
    unittest.main()
