# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic import db

from .testbase import get_test_db_uri, teardown_test_db


class Issue221TestCase(unittest.TestCase):
    def setUp(self):
        uri, self.__tmp = get_test_db_uri(memory=True)
        db.init_database(uri)
        root = db.Folder.create(root=True, name="Folder", path="tests")
        artist = db.Artist.create(name="Artist")
        album = db.Album.create(artist=artist, name="Album")

        for i in range(3):
            db.Track.create(
                title=f"Track {i}",
                album=album,
                artist=artist,
                disc=1,
                number=i + 1,
                duration=3,
                has_art=False,
                bitrate=64,
                path=f"tests/track{i}",
                last_modification=2,
                root_folder=root,
                folder=root,
                genre="Genre",
            )

        db.User.create(name="user", password="secret", salt="sugar")

    def tearDown(self):
        teardown_test_db(self.__tmp)

    def test_issue(self):
        data = db.Album.get().as_subsonic_album(db.User.get())
        self.assertIn("genre", data)
        self.assertEqual(data["genre"], "Genre")


if __name__ == "__main__":
    unittest.main()
