# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import shutil
import tempfile
import unittest

from supysonic.db import Track, init_database
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

from .testbase import get_test_db_uri, teardown_test_db


class Issue139TestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()
        uri, self.__tmp = get_test_db_uri(memory=True)
        init_database(uri)
        FolderManager().add("folder", self.__dir)

    def tearDown(self):
        teardown_test_db(self.__tmp)
        shutil.rmtree(self.__dir)

    def do_scan(self):
        scanner = Scanner()
        scanner.queue_folder("folder")
        scanner.run()

    def test_null_genre(self):
        shutil.copy("tests/assets/issue139.mp3", self.__dir)
        self.do_scan()

        # A missing ID3 genre used to raise IndexError; the file must scan with genre None.
        self.assertEqual(Track.select().count(), 1)
        self.assertIsNone(Track.select().first().genre)


if __name__ == "__main__":
    unittest.main()
