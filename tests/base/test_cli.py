# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import os
import shutil
import tempfile
import unittest

from contextlib import contextmanager
from StringIO import StringIO

from supysonic.db import Folder, User, get_store
from supysonic.cli import SupysonicCLI

from ..testbase import TestConfig

class CLITestCase(unittest.TestCase):
    """ Really basic tests. Some even don't check anything but are juste there for coverage """

    def setUp(self):
        conf = TestConfig(False, False)
        self.__dbfile = tempfile.mkstemp()[1]
        conf.BASE['database_uri'] = 'sqlite:///' + self.__dbfile
        self.__store = get_store(conf.BASE['database_uri'])

        with io.open('schema/sqlite.sql', 'r') as sql:
            schema = sql.read()
            for statement in schema.split(';'):
                self.__store.execute(statement)
        self.__store.commit()

        self.__stdout = StringIO()
        self.__stderr = StringIO()
        self.__cli = SupysonicCLI(conf, stdout = self.__stdout, stderr = self.__stderr)

    def tearDown(self):
        self.__stdout.close()
        self.__stderr.close()
        self.__store.close()
        os.unlink(self.__dbfile)

    @contextmanager
    def _tempdir(self):
        d = tempfile.mkdtemp()
        try:
            yield d
        finally:
            shutil.rmtree(d)

    def test_folder_add(self):
        with self._tempdir() as d:
            self.__cli.onecmd('folder add tmpfolder ' + d)

        f = self.__store.find(Folder).one()
        self.assertIsNotNone(f)
        self.assertEqual(f.path, d)

    def test_folder_add_errors(self):
        with self._tempdir() as d:
            self.__cli.onecmd('folder add f1 ' + d)
            self.__cli.onecmd('folder add f2 ' + d)
        with self._tempdir() as d:
            self.__cli.onecmd('folder add f1 ' + d)
        self.__cli.onecmd('folder add f3 /invalid/path')

        self.assertEqual(self.__store.find(Folder).count(), 1)

    def test_folder_delete(self):
        with self._tempdir() as d:
            self.__cli.onecmd('folder add tmpfolder ' + d)
        self.__cli.onecmd('folder delete randomfolder')
        self.__cli.onecmd('folder delete tmpfolder')
        self.assertEqual(self.__store.find(Folder).count(), 0)

    def test_folder_list(self):
        with self._tempdir() as d:
            self.__cli.onecmd('folder add tmpfolder ' + d)
            self.__cli.onecmd('folder list')
            self.assertIn('tmpfolder', self.__stdout.getvalue())
            self.assertIn(d, self.__stdout.getvalue())

    def test_folder_scan(self):
        with self._tempdir() as d:
            self.__cli.onecmd('folder add tmpfolder ' + d)
            with tempfile.NamedTemporaryFile(dir = d):
                self.__cli.onecmd('folder scan')
                self.__cli.onecmd('folder scan tmpfolder nonexistent')

    def test_user_add(self):
        self.__cli.onecmd('user add -p Alic3 alice')
        self.__cli.onecmd('user add -p alice alice')
        self.assertEqual(self.__store.find(User).count(), 1)

    def test_user_delete(self):
        self.__cli.onecmd('user add -p Alic3 alice')
        self.__cli.onecmd('user delete alice')
        self.__cli.onecmd('user delete bob')
        self.assertEqual(self.__store.find(User).count(), 0)

    def test_user_list(self):
        self.__cli.onecmd('user add -p Alic3 alice')
        self.__cli.onecmd('user list')
        self.assertIn('alice', self.__stdout.getvalue())

    def test_user_setadmin(self):
        self.__cli.onecmd('user add -p Alic3 alice')
        self.__cli.onecmd('user setadmin alice')
        self.__cli.onecmd('user setadmin bob')
        self.assertTrue(self.__store.find(User, User.name == 'alice').one().admin)

    def test_user_changepass(self):
        self.__cli.onecmd('user add -p Alic3 alice')
        self.__cli.onecmd('user changepass alice newpass')
        self.__cli.onecmd('user changepass bob B0b')

    def test_other(self):
        self.assertTrue(self.__cli.do_EOF(''))
        self.__cli.onecmd('unknown command')
        self.__cli.postloop()
        self.__cli.completedefault('user', 'user', 4, 4)

if __name__ == "__main__":
    unittest.main()

