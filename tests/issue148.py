# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import shutil
import sys
import tempfile
import unittest

from supysonic.db import init_database, release_database, Folder, Track
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner


@unittest.skipIf(sys.platform == "win32", "Windows doesn't allow space-only filenames")
class Issue148TestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()
        init_database("sqlite:")
        FolderManager.add("folder", self.__dir)

    def tearDown(self):
        release_database()
        shutil.rmtree(self.__dir)

    def test_issue(self):
        subdir = os.path.join(self.__dir, "  ")
        os.makedirs(subdir)
        shutil.copyfile(
            "tests/assets/folder/silence.mp3", os.path.join(subdir, "silence.mp3")
        )

        scanner = Scanner()
        scanner.queue_folder("folder")
        scanner.run()

        # The whitespace-only directory used to yield an empty Folder.name (ValueError).
        # The scan must complete, create the child folder and add the contained track.
        self.assertEqual(Track.select().count(), 1)
        self.assertGreaterEqual(Folder.select().where(~Folder.root).count(), 1)


if __name__ == "__main__":
    unittest.main()
