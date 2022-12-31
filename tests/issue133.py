# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import shutil
import tempfile
import unittest

from supysonic.db import init_database, release_database
from supysonic.db import Track
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner


class Issue133TestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()
        shutil.copy("tests/assets/issue133.flac", self.__dir)
        init_database("sqlite:")
        FolderManager.add("folder", self.__dir)

    def tearDown(self):
        release_database()
        shutil.rmtree(self.__dir)

    def test_issue133(self):
        scanner = Scanner()
        scanner.queue_folder("folder")
        scanner.run()

        track = Track.select().first()
        self.assertNotIn("\x00", track.title)


if __name__ == "__main__":
    unittest.main()
