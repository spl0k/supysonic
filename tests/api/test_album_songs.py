# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.db import (
    Folder,
    Artist,
    Album,
    Track,
    StarredArtist,
    StarredAlbum,
    StarredFolder,
    StarredTrack,
    User,
)

from .apitestbase import ApiTestBase


class AlbumSongsTestCase(ApiTestBase):
    # I'm too lazy to write proper tests concerning the data on those endpoints
    # Let's just check paramter validation and ensure coverage

    def setUp(self):
        super().setUp()

        folder = Folder.create(name="Root", root=True, path="tests/assets")
        empty = Folder.create(name="Root", root=True, path="/tmp")
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        Track.create(
            title="Track 1",
            album=album,
            artist=artist,
            disc=1,
            number=1,
            year=123,
            path="tests/assets/folder/1",
            folder=folder,
            root_folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )
        Track.create(
            title="Track 2",
            album=album,
            artist=artist,
            disc=1,
            number=1,
            year=124,
            genre="Lampshade",
            path="tests/assets/folder/2",
            folder=folder,
            root_folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

    def test_get_album_list(self):
        self._make_request("getAlbumList", error=10)
        self._make_request("getAlbumList", {"type": "kraken"}, error=0)
        self._make_request("getAlbumList", {"type": "random", "size": "huge"}, error=0)
        self._make_request(
            "getAlbumList", {"type": "newest", "offset": "minus one"}, error=0
        )
        self._make_request("getAlbumList", {"type": "byYear"}, error=10)
        self._make_request(
            "getAlbumList",
            {"type": "byYear", "fromYear": "Epoch", "toYear": "EOL"},
            error=0,
        )
        self._make_request("getAlbumList", {"type": "byGenre"}, error=10)
        self._make_request(
            "getAlbumList", {"type": "random", "musicFolderId": "id"}, error=0
        )
        self._make_request(
            "getAlbumList", {"type": "random", "musicFolderId": 12}, error=70
        )

        types_and_count = [
            ("random", 1),
            ("newest", 1),
            ("highest", 1),
            ("frequent", 1),
            ("recent", 0),  # never played
            ("alphabeticalByName", 1),
            (
                "alphabeticalByArtist",
                0,  # somehow expected due to funky "album" definition on this endpoint
            ),
            ("starred", 0),  # nothing's starred
        ]
        for t, c in types_and_count:
            rv, child = self._make_request(
                "getAlbumList", {"type": t}, tag="albumList", skip_post=t == "random"
            )
            self.assertEqual(len(child), c)

        rv, child = self._make_request(
            "getAlbumList",
            {"type": "byYear", "fromYear": 100, "toYear": 200},
            tag="albumList",
        )
        self.assertEqual(len(child), 1)
        rv, child = self._make_request(
            "getAlbumList",
            {"type": "byYear", "fromYear": 200, "toYear": 300},
            tag="albumList",
        )
        self.assertEqual(len(child), 0)
        # Need more data to properly test ordering
        rv, child = self._make_request(
            "getAlbumList",
            {"type": "byYear", "fromYear": 200, "toYear": 100},
            tag="albumList",
        )
        self.assertEqual(len(child), 1)

        rv, child = self._make_request(
            "getAlbumList", {"type": "byGenre", "genre": "FARTS"}, tag="albumList"
        )
        self.assertEqual(len(child), 0)

        rv, child = self._make_request(
            "getAlbumList", {"type": "byGenre", "genre": "Lampshade"}, tag="albumList"
        )
        self.assertEqual(len(child), 1)

        _, child = self._make_request(
            "getAlbumList",
            {"musicFolderId": 1, "type": "alphabeticalByName"},
            tag="albumList",
        )
        self.assertEqual(len(child), 1)
        _, child = self._make_request(
            "getAlbumList",
            {"musicFolderId": 2, "type": "alphabeticalByName"},
            tag="albumList",
        )
        self.assertEqual(len(child), 0)

        Track.delete().execute()
        Folder[1].delete_instance()
        rv, child = self._make_request(
            "getAlbumList", {"type": "random"}, tag="albumList"
        )
        self.assertEqual(len(child), 0)

    def test_get_album_list2(self):
        self._make_request("getAlbumList2", error=10)
        self._make_request("getAlbumList2", {"type": "void"}, error=0)
        self._make_request(
            "getAlbumList2", {"type": "random", "size": "size_t"}, error=0
        )
        self._make_request(
            "getAlbumList2", {"type": "newest", "offset": "&v + 2"}, error=0
        )
        self._make_request("getAlbumList2", {"type": "byYear"}, error=10)
        self._make_request(
            "getAlbumList2",
            {"type": "byYear", "fromYear": "Epoch", "toYear": "EOL"},
            error=0,
        )
        self._make_request("getAlbumList2", {"type": "byGenre"}, error=10)
        self._make_request(
            "getAlbumList2", {"type": "random", "musicFolderId": "id"}, error=0
        )
        self._make_request(
            "getAlbumList2", {"type": "random", "musicFolderId": 12}, error=70
        )

        types = [
            "random",
            "newest",
            "frequent",
            "recent",
            "starred",
            "alphabeticalByName",
            "alphabeticalByArtist",
        ]
        for t in types:
            self._make_request(
                "getAlbumList2", {"type": t}, tag="albumList2", skip_post=t == "random"
            )

        self._make_request(
            "getAlbumList2", {"type": "random"}, tag="albumList2", skip_post=True
        )

        rv, child = self._make_request(
            "getAlbumList2",
            {"type": "byYear", "fromYear": 100, "toYear": 200},
            tag="albumList2",
        )
        self.assertEqual(len(child), 1)
        rv, child = self._make_request(
            "getAlbumList2",
            {"type": "byYear", "fromYear": 200, "toYear": 300},
            tag="albumList2",
        )
        self.assertEqual(len(child), 0)
        # Need more data to properly test ordering
        rv, child = self._make_request(
            "getAlbumList2",
            {"type": "byYear", "fromYear": 200, "toYear": 100},
            tag="albumList2",
        )
        self.assertEqual(len(child), 1)

        rv, child = self._make_request(
            "getAlbumList2", {"type": "byGenre", "genre": "FARTS"}, tag="albumList2"
        )
        self.assertEqual(len(child), 0)

        rv, child = self._make_request(
            "getAlbumList2", {"type": "byGenre", "genre": "Lampshade"}, tag="albumList2"
        )
        self.assertEqual(len(child), 1)

        _, child = self._make_request(
            "getAlbumList2",
            {"musicFolderId": 1, "type": "alphabeticalByName"},
            tag="albumList2",
        )
        self.assertEqual(len(child), 1)
        _, child = self._make_request(
            "getAlbumList2",
            {"musicFolderId": 2, "type": "alphabeticalByName"},
            tag="albumList2",
        )
        self.assertEqual(len(child), 0)

        Track.delete().execute()
        Album.delete().execute()
        rv, child = self._make_request(
            "getAlbumList2", {"type": "random"}, tag="albumList2"
        )
        self.assertEqual(len(child), 0)

    def test_get_random_songs(self):
        self._make_request("getRandomSongs", {"size": "8 floors"}, error=0)
        self._make_request("getRandomSongs", {"fromYear": "year"}, error=0)
        self._make_request("getRandomSongs", {"toYear": "year"}, error=0)
        self._make_request("getRandomSongs", {"musicFolderId": "idid"}, error=0)
        self._make_request("getRandomSongs", {"musicFolderId": 1234567890}, error=70)

        rv, child = self._make_request(
            "getRandomSongs", tag="randomSongs", skip_post=True
        )

        self._make_request(
            "getRandomSongs",
            {
                "fromYear": -52,
                "toYear": "1984",
                "genre": "some cryptic subgenre youve never heard of",
                "musicFolderId": 1,
            },
            tag="randomSongs",
        )

    def test_now_playing(self):
        self._make_request("getNowPlaying", tag="nowPlaying")

    def _create_starred_info(self):
        user = User.select().first()
        StarredArtist.create(user=user, starred=Artist.select().first())
        StarredAlbum.create(user=user, starred=Album.select().first())
        StarredTrack.create(user=user, starred=Track.select().first())
        StarredFolder.create(user=user, starred=Folder.select().first())

    def test_get_starred(self):
        self._create_starred_info()

        self._make_request("getStarred", tag="starred")
        self._make_request("getStarred", {"musicFolderId": 1}, tag="starred")

    def test_get_starred2(self):
        self._create_starred_info()

        self._make_request("getStarred2", tag="starred2")
        self._make_request("getStarred2", {"musicFolderId": 1}, tag="starred2")

    def test_get_songs_by_genre(self):
        self._make_request("getSongsByGenre", error=10)
        self._make_request(
            "getSongsByGenre", {"genre": "genre", "musicFolderId": "idid"}, error=0
        )
        self._make_request(
            "getSongsByGenre", {"genre": "genre", "musicFolderId": 1234567890}, error=70
        )
        self._make_request(
            "getSongsByGenre", {"genre": "genre", "count": "three"}, error=0
        )
        self._make_request(
            "getSongsByGenre", {"genre": "genre", "offset": "four"}, error=0
        )

        rv, child = self._make_request(
            "getSongsByGenre", {"genre": "Lampshade"}, tag="songsByGenre"
        )
        self.assertEqual(len(child), 1)


if __name__ == "__main__":
    unittest.main()
