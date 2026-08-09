# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.db import (
    Album,
    Artist,
    Folder,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
    User,
    now,
)

from .apitestbase import ApiTestBase


class AlbumSongsTestCase(ApiTestBase):
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

        # out of range paging
        self._make_request("getAlbumList", {"type": "random", "size": -1}, error=0)
        self._make_request("getAlbumList", {"type": "random", "size": 100000}, error=0)
        self._make_request("getAlbumList", {"type": "newest", "offset": -1}, error=0)

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

        # out of range paging
        self._make_request("getAlbumList2", {"type": "random", "size": -1}, error=0)
        self._make_request("getAlbumList2", {"type": "random", "size": 100000}, error=0)
        self._make_request("getAlbumList2", {"type": "newest", "offset": -1}, error=0)

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
        self._make_request("getRandomSongs", {"size": -1}, error=0)
        self._make_request("getRandomSongs", {"size": 100000}, error=0)

        rv, child = self._make_request(
            "getRandomSongs", tag="randomSongs", skip_post=True
        )
        # Only two tracks are seeded; an unfiltered request returns them both.
        self.assertEqual(len(child), 2)

        _, child = self._make_request(
            "getRandomSongs",
            {
                "fromYear": -52,
                "toYear": "1984",
                "genre": "some cryptic subgenre youve never heard of",
                "musicFolderId": 1,
            },
            tag="randomSongs",
            skip_post=True,
        )
        # No track matches that genre.
        self.assertEqual(len(child), 0)

    def test_now_playing(self):
        _, child = self._make_request("getNowPlaying", tag="nowPlaying")
        self.assertEqual(len(child), 0)

        user = User.get(name="alice")
        user.last_play = Track.select().first()
        user.last_play_date = now()
        user.save()

        _, child = self._make_request("getNowPlaying", tag="nowPlaying")
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("username"), "alice")

    def _create_starred_info(self):
        user = User.get(User.name == "alice")
        StarredArtist.create(user=user, starred=Artist.select().first())
        StarredAlbum.create(user=user, starred=Album.select().first())
        StarredTrack.create(user=user, starred=Track.select().first())
        StarredFolder.create(user=user, starred=Folder.select().first())

    def test_get_starred(self):
        self._create_starred_info()

        # getStarred is folder-based: the starred folder holds tracks so it surfaces as an
        # album (not an artist), plus the directly starred song.
        _, child = self._make_request("getStarred", tag="starred")
        self.assertEqual(len(self._xpath(child, "./artist")), 0)
        self.assertEqual(len(self._xpath(child, "./album")), 1)
        self.assertEqual(len(self._xpath(child, "./song")), 1)

        _, child = self._make_request("getStarred", {"musicFolderId": 1}, tag="starred")
        self.assertEqual(len(self._xpath(child, "./song")), 1)

    def test_get_starred2(self):
        self._create_starred_info()

        # getStarred2 is tag-based: one starred artist, album and song each.
        _, child = self._make_request("getStarred2", tag="starred2")
        self.assertEqual(len(self._xpath(child, "./artist")), 1)
        self.assertEqual(len(self._xpath(child, "./album")), 1)
        self.assertEqual(len(self._xpath(child, "./song")), 1)

        _, child = self._make_request(
            "getStarred2", {"musicFolderId": 1}, tag="starred2"
        )
        self.assertEqual(len(self._xpath(child, "./song")), 1)

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
        self._make_request("getSongsByGenre", {"genre": "genre", "count": -1}, error=0)
        self._make_request(
            "getSongsByGenre", {"genre": "genre", "count": 100000}, error=0
        )
        self._make_request("getSongsByGenre", {"genre": "genre", "offset": -1}, error=0)

        rv, child = self._make_request(
            "getSongsByGenre", {"genre": "Lampshade"}, tag="songsByGenre"
        )
        self.assertEqual(len(child), 1)

        # Filtered by an existing music folder (exercises the root-folder filter)
        rv, child = self._make_request(
            "getSongsByGenre",
            {"genre": "Lampshade", "musicFolderId": 1},
            tag="songsByGenre",
        )
        self.assertEqual(len(child), 1)

        # The other (empty) root has no such song
        rv, child = self._make_request(
            "getSongsByGenre",
            {"genre": "Lampshade", "musicFolderId": 2},
            tag="songsByGenre",
        )
        self.assertEqual(len(child), 0)

    def _seed_paging_library(self, count=7):
        """Create `count` same-genre tracks spread over albums sharing a name.

        The duplicate album/artist names make every non-unique sort key tie, so
        paging is only stable if the queries fall back to a primary key.
        """
        folder = Folder.get(Folder.path == "tests/assets")
        for i in range(count):
            artist = Artist.create(name="Paging Artist")
            album = Album.create(name="Paging Album", artist=artist)
            Track.create(
                title="Paging Track",
                album=album,
                artist=artist,
                disc=1,
                number=1,
                year=2000,
                genre="Paging",
                path=f"tests/assets/paging/{i}",
                folder=folder,
                root_folder=folder,
                duration=2,
                bitrate=320,
                last_modification=0,
            )

    def _walk_pages(self, endpoint, args, tag, count_param, page_size, total):
        """Request `endpoint` page by page, returning the concatenated ids."""
        ids = []
        for offset in range(0, total + page_size, page_size):
            _, child = self._make_request(
                endpoint,
                dict(args, **{count_param: page_size, "offset": offset}),
                tag=tag,
                skip_post=True,
            )
            ids += [e.get("id") for e in child]
        return ids

    def test_get_songs_by_genre_paging(self):
        self._seed_paging_library()

        _, child = self._make_request(
            "getSongsByGenre",
            {"genre": "Paging", "count": 100},
            tag="songsByGenre",
            skip_post=True,
        )
        expected = [e.get("id") for e in child]
        self.assertEqual(len(expected), 7)

        paged = self._walk_pages(
            "getSongsByGenre", {"genre": "Paging"}, "songsByGenre", "count", 2, 7
        )
        self.assertEqual(len(set(paged)), len(paged))  # no duplicates
        self.assertEqual(paged, expected)  # nothing skipped, same order

    def test_get_album_list_paging(self):
        self._seed_paging_library()

        for endpoint, tag in (
            ("getAlbumList", "albumList"),
            ("getAlbumList2", "albumList2"),
        ):
            for ltype in (
                "alphabeticalByName",
                "alphabeticalByArtist",
                "newest",
                "byGenre",
            ):
                args = {"type": ltype}
                if ltype == "byGenre":
                    args["genre"] = "Paging"

                _, child = self._make_request(
                    endpoint, dict(args, size=100), tag=tag, skip_post=True
                )
                expected = [e.get("id") for e in child]

                paged = self._walk_pages(endpoint, args, tag, "size", 2, len(expected))
                with self.subTest(endpoint=endpoint, type=ltype):
                    self.assertEqual(len(set(paged)), len(paged))
                    self.assertEqual(paged, expected)


if __name__ == "__main__":
    unittest.main()
