# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import os.path
import shutil
import sys
import tempfile
import unittest

from supysonic.db import Track, init_database
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

from .testbase import get_test_db_uri, teardown_test_db


@unittest.skipIf(
    sys.platform == "win32", "Windows doesn't seem too allow badly encoded paths"
)
class Issue85TestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()
        uri, self.__tmp = get_test_db_uri(memory=True)
        init_database(uri)
        FolderManager.add("folder", self.__dir)

    def tearDown(self):
        teardown_test_db(self.__tmp)
        shutil.rmtree(self.__dir)

    def test_issue(self):
        os.mkdir(os.path.join(self.__dir.encode(), b"\xe6"))
        shutil.copyfile(
            "tests/assets/folder/silence.mp3",
            os.path.join(self.__dir.encode(), b"\xe6", b"silence.mp3"),
        )

        scanner = Scanner()
        scanner.queue_folder("folder")
        scanner.run()

        # The badly encoded path must not crash the scan: the file is skipped
        self.assertEqual(Track.select().count(), 0)
        self.assertEqual(len(scanner.stats().errors), 1)


if __name__ == "__main__":
    unittest.main()
