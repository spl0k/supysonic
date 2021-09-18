# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from pony.orm import db_session

from supysonic import db


class Issue221TestCase(unittest.TestCase):
    def setUp(self):
        db.init_database("sqlite:")
        with db_session:
            root = db.Folder(root=True, name="Folder", path="tests")
            artist = db.Artist(name="Artist")
            album = db.Album(artist=artist, name="Album")

            for i in range(3):
                db.Track(
                    title="Track {}".format(i),
                    album=album,
                    artist=artist,
                    disc=1,
                    number=i + 1,
                    duration=3,
                    has_art=False,
                    bitrate=64,
                    path="tests/track{}".format(i),
                    last_modification=2,
                    root_folder=root,
                    folder=root,
                    genre="Genre",
                )

            db.User(name="user", password="secret", salt="sugar")

    def tearDown(self):
        db.release_database()

    @db_session
    def test_issue(self):
        data = db.Album.get().as_subsonic_album(db.User.get())
        self.assertIn("genre", data)
        self.assertEqual(data["genre"], "Genre")


if __name__ == "__main__":
    unittest.main()
