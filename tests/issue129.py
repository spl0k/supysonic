# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest

from pony.orm import db_session

from supysonic.db import User, Track, StarredTrack, RatingTrack
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

from .testbase import TestBase


class Issue129TestCase(TestBase):
    def setUp(self):
        super(Issue129TestCase, self).setUp()

        with db_session:
            folder = FolderManager.add("folder", os.path.abspath("tests/assets/folder"))
            scanner = Scanner()
            scanner.queue_folder("folder")
            scanner.run()

            self.trackid = Track.select().first().id
            self.userid = User.get(name="alice").id

    def test_last_play(self):
        with db_session:
            User[self.userid].last_play = Track[self.trackid]
        with db_session:
            FolderManager.delete_by_name("folder")

    def test_starred(self):
        with db_session:
            StarredTrack(user=self.userid, starred=self.trackid)
            FolderManager.delete_by_name("folder")

    def test_rating(self):
        with db_session:
            RatingTrack(user=self.userid, rated=self.trackid, rating=5)
            FolderManager.delete_by_name("folder")


if __name__ == "__main__":
    unittest.main()
