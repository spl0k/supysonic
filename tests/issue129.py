# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest

from supysonic.db import Folder, RatingTrack, StarredTrack, Track, User
from supysonic.scanner import Scanner

from .testbase import TestBase


class Issue129TestCase(TestBase):
    def setUp(self):
        super().setUp()

        self._app_layer.folders.add("folder", os.path.abspath("tests/assets/folder"))
        scanner = Scanner()
        scanner.queue_folder("folder")
        scanner.run()

        self.trackid = Track.select().first().id
        self.userid = User.get(name="alice").id

    def test_last_play(self):
        user = User[self.userid]
        user.last_play = Track[self.trackid]
        user.save()

        # Deleting the folder used to fail on a foreign key constraint because the
        # user still referenced one of the deleted tracks.
        self._app_layer.folders.delete_by_name("folder")

        self.assertEqual(Folder.select().count(), 0)
        self.assertEqual(Track.select().count(), 0)
        self.assertIsNone(User[self.userid].last_play)

    def test_starred(self):
        StarredTrack.create(user=self.userid, starred=self.trackid)
        self._app_layer.folders.delete_by_name("folder")

        self.assertEqual(Folder.select().count(), 0)
        self.assertEqual(Track.select().count(), 0)
        self.assertEqual(StarredTrack.select().count(), 0)

    def test_rating(self):
        RatingTrack.create(user=self.userid, rated=self.trackid, rating=5)
        self._app_layer.folders.delete_by_name("folder")

        self.assertEqual(Folder.select().count(), 0)
        self.assertEqual(Track.select().count(), 0)
        self.assertEqual(RatingTrack.select().count(), 0)


if __name__ == "__main__":
    unittest.main()
