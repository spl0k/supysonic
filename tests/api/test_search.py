# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import time
import unittest

from supysonic.db import Folder, Artist, Album, Track

from ._dataset import (
    ALBUM_COUNT,
    ARTIST_COUNT,
    FOLDER_COUNT,
    ROOT_COUNT,
    TRACK_COUNT,
    populate_library,
)
from .apitestbase import ApiTestBase


class SearchTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        self.lib = populate_library()

        self.assertEqual(Folder.select().count(), FOLDER_COUNT)
        self.assertEqual(Folder.select().where(Folder.root).count(), ROOT_COUNT)
        self.assertEqual(Artist.select().count(), ARTIST_COUNT)
        self.assertEqual(Album.select().count(), ALBUM_COUNT)
        self.assertEqual(Track.select().count(), TRACK_COUNT)

    def __track_as_pseudo_unique_str(self, elem):
        return elem.get("artist") + elem.get("album") + elem.get("title")

    def test_search(self):
        # invalid parameters
        self._make_request("search", {"count": "string"}, error=0)
        self._make_request("search", {"offset": "sstring"}, error=0)
        self._make_request("search", {"newerThan": "ssstring"}, error=0)

        # no search
        self._make_request("search", error=10)

        # 'search' matches folder names (not artist/album tags), so a tag-only
        # name finds nothing here (compare with search3).
        rv, child = self._make_request(
            "search", {"artist": "Floyd"}, tag="searchResult"
        )
        self.assertEqual(len(child), 0)

        # artist search matches folders that have track-bearing subfolders
        rv, child = self._make_request("search", {"artist": "Rock"}, tag="searchResult")
        self.assertEqual(len(child), 1)
        self.assertEqual(child.get("totalHits"), "1")
        self.assertEqual(child[0].get("title"), "Rock")

        rv, child = self._make_request("search", {"artist": "Jazz"}, tag="searchResult")
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("title"), "Jazz")

        # album search matches folders that directly contain tracks
        rv, child = self._make_request(
            "search", {"album": "Dark Side"}, tag="searchResult"
        )
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("title"), "Dark Side")
        self.assertEqual(child[0].get("artist"), "Rock")

        # title search matches track titles
        rv, child = self._make_request(
            "search", {"title": "Money"}, tag="searchResult"
        )
        self.assertEqual(len(child), 2)
        for c in child:
            self.assertIn("Money", c.get("title"))

        rv, child = self._make_request("search", {"title": "Time"}, tag="searchResult")
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("title"), "Time")

        # same as above, but created in the future
        future = int(time.time() * 1000 + 1000)
        rv, child = self._make_request(
            "search", {"title": "Money", "newerThan": future}, tag="searchResult"
        )
        self.assertEqual(len(child), 0)

        # any field search: folders by name + tracks by title
        rv, child = self._make_request(
            "search", {"any": "Money"}, tag="searchResult"
        )
        self.assertEqual(len(child), 2)  # the two "Money" tracks, no folder named so

        rv, child = self._make_request("search", {"any": "Jazz"}, tag="searchResult")
        self.assertEqual(len(child), 1)  # the "Jazz" folder

        rv, child = self._make_request(
            "search", {"any": "Money", "newerThan": future}, tag="searchResult"
        )
        self.assertEqual(len(child), 0)

        # paging over the title search
        rv, child = self._make_request("search", {"title": "e"}, tag="searchResult")
        total = int(child.get("totalHits"))
        self.assertGreater(total, 2)

        songs = []
        for offset in range(0, total, 2):
            rv, child = self._make_request(
                "search",
                {"title": "e", "count": 2, "offset": offset},
                tag="searchResult",
            )
            self.assertEqual(child.get("totalHits"), str(total))
            self.assertEqual(child.get("offset"), str(offset))
            self.assertLessEqual(len(child), 2)
            for song in map(self.__track_as_pseudo_unique_str, child):
                self.assertNotIn(song, songs)
                songs.append(song)
        self.assertEqual(len(songs), total)

    def test_search2(self):
        # invalid parameters
        self._make_request("search2", {"query": "a", "artistCount": "string"}, error=0)
        self._make_request(
            "search2", {"query": "a", "artistOffset": "sstring"}, error=0
        )
        self._make_request("search2", {"query": "a", "albumCount": "string"}, error=0)
        self._make_request("search2", {"query": "a", "albumOffset": "sstring"}, error=0)
        self._make_request("search2", {"query": "a", "songCount": "string"}, error=0)
        self._make_request("search2", {"query": "a", "songOffset": "sstring"}, error=0)
        self._make_request(
            "search2", {"query": "a", "musicFolderId": "sstring"}, error=0
        )
        self._make_request("search2", {"query": "a", "musicFolderId": -2}, error=70)

        # no search
        self._make_request("search2", error=10)

        # non existent anything
        rv, child = self._make_request(
            "search2", {"query": "Chaos"}, tag="searchResult2"
        )
        self.assertEqual(len(child), 0)

        # search2 matches folder names. A tag-only name (artist/album) finds
        # nothing -- this is what distinguishes it from search3.
        rv, child = self._make_request(
            "search2", {"query": "Floyd"}, tag="searchResult2"
        )
        self.assertEqual(len(child), 0)

        # "Rock" is a folder with a track-bearing subfolder (-> artist) and also
        # directly holds a track (-> album), but no track title contains it.
        rv, child = self._make_request("search2", {"query": "Rock"}, tag="searchResult2")
        self.assertEqual(len(self._xpath(child, "./artist")), 1)
        self.assertEqual(len(self._xpath(child, "./album")), 1)
        self.assertEqual(len(self._xpath(child, "./song")), 0)
        self.assertEqual(self._xpath(child, "./artist/@name")[0], "Rock")

        # "Jazz" is an artist-folder but holds no track directly -> no album
        rv, child = self._make_request("search2", {"query": "Jazz"}, tag="searchResult2")
        self.assertEqual(len(self._xpath(child, "./artist")), 1)
        self.assertEqual(len(self._xpath(child, "./album")), 0)
        self.assertEqual(len(self._xpath(child, "./song")), 0)

        # song search
        rv, child = self._make_request(
            "search2", {"query": "Money"}, tag="searchResult2"
        )
        self.assertEqual(len(self._xpath(child, "./artist")), 0)
        self.assertEqual(len(self._xpath(child, "./album")), 0)
        songs = self._xpath(child, "./song")
        self.assertEqual(len(songs), 2)
        self.assertSequenceEqual(
            sorted(s.get("title") for s in songs), ["Money", "Money (Live)"]
        )

        # paging - artists matching "c" (Music + Rock)
        artists = []
        for offset in range(0, 4, 2):
            rv, child = self._make_request(
                "search2",
                {"query": "c", "artistCount": 2, "artistOffset": offset},
                tag="searchResult2",
            )
            names = self._xpath(child, "./artist/@name")
            self.assertLessEqual(len(names), 2)
            for name in names:
                self.assertNotIn(name, artists)
                artists.append(name)
        self.assertSequenceEqual(sorted(artists), ["Music", "Rock"])

        # paging - songs matching "e"
        rv, child = self._make_request("search2", {"query": "e"}, tag="searchResult2")
        total = len(self._xpath(child, "./song"))
        self.assertGreater(total, 2)
        songs = []
        for offset in range(0, total, 2):
            rv, child = self._make_request(
                "search2",
                {"query": "e", "songCount": 2, "songOffset": offset},
                tag="searchResult2",
            )
            elems = self._xpath(child, "./song")
            self.assertLessEqual(len(elems), 2)
            for song in map(self.__track_as_pseudo_unique_str, elems):
                self.assertNotIn(song, songs)
                songs.append(song)
        self.assertEqual(len(songs), total)

        # root filtering
        _, child = self._make_request(
            "search2", {"query": "Money", "musicFolderId": 1}, tag="searchResult2"
        )
        self.assertEqual(len(self._xpath(child, "./song")), 2)

        _, child = self._make_request(
            "search2", {"query": "Money", "musicFolderId": 2}, tag="searchResult2"
        )
        self.assertEqual(len(self._xpath(child, "./song")), 0)

    def test_search3(self):
        # invalid parameters
        self._make_request("search3", {"query": "a", "artistCount": "string"}, error=0)
        self._make_request(
            "search3", {"query": "a", "artistOffset": "sstring"}, error=0
        )
        self._make_request("search3", {"query": "a", "albumCount": "string"}, error=0)
        self._make_request("search3", {"query": "a", "albumOffset": "sstring"}, error=0)
        self._make_request("search3", {"query": "a", "songCount": "string"}, error=0)
        self._make_request("search3", {"query": "a", "songOffset": "sstring"}, error=0)
        self._make_request(
            "search3", {"query": "a", "musicFolderId": "sstring"}, error=0
        )
        self._make_request("search3", {"query": "a", "musicFolderId": -2}, error=70)

        # no search
        self._make_request("search3", error=10)

        # non existent anything
        rv, child = self._make_request(
            "search3", {"query": "Chaos"}, tag="searchResult3"
        )
        self.assertEqual(len(child), 0)

        # search3 matches artist/album *tags*. "Floyd"/"Davis" are artist names
        # with no matching folder, so search2 returns nothing for them but
        # search3 finds the artist.
        rv, child = self._make_request(
            "search3", {"query": "Floyd"}, tag="searchResult3"
        )
        self.assertEqual(len(self._xpath(child, "./artist")), 1)
        self.assertEqual(len(self._xpath(child, "./album")), 0)
        self.assertEqual(len(self._xpath(child, "./song")), 0)
        self.assertEqual(child[0].get("name"), "Pink Floyd")

        rv, child = self._make_request(
            "search3", {"query": "Davis"}, tag="searchResult3"
        )
        self.assertEqual(len(self._xpath(child, "./artist")), 1)
        self.assertEqual(child[0].get("name"), "Miles Davis")

        # Conversely, "Rock" is a folder name only -> no tag match
        rv, child = self._make_request("search3", {"query": "Rock"}, tag="searchResult3")
        self.assertEqual(len(child), 0)

        # "Jazz" matches an album tag (the compilation), not an artist
        rv, child = self._make_request("search3", {"query": "Jazz"}, tag="searchResult3")
        self.assertEqual(len(self._xpath(child, "./artist")), 0)
        self.assertEqual(len(self._xpath(child, "./album")), 1)
        self.assertEqual(len(self._xpath(child, "./song")), 0)
        self.assertEqual(child[0].get("name"), "Greatest Jazz Hits")

        # album + song tag match
        rv, child = self._make_request("search3", {"query": "Blue"}, tag="searchResult3")
        self.assertEqual(len(self._xpath(child, "./artist")), 0)
        self.assertEqual(len(self._xpath(child, "./album")), 1)
        self.assertEqual(len(self._xpath(child, "./song")), 1)
        self.assertEqual(self._xpath(child, "./album/@name")[0], "Kind of Blue")
        self.assertEqual(self._xpath(child, "./song/@title")[0], "Blue in Green")

        # song search
        rv, child = self._make_request(
            "search3", {"query": "Money"}, tag="searchResult3"
        )
        self.assertEqual(len(self._xpath(child, "./artist")), 0)
        self.assertEqual(len(self._xpath(child, "./album")), 0)
        songs = self._xpath(child, "./song")
        self.assertEqual(len(songs), 2)
        self.assertSequenceEqual(
            sorted(s.get("title") for s in songs), ["Money", "Money (Live)"]
        )

        # paging - artists matching "a" (Clare Torry, Miles Davis, Various Artists)
        artists = []
        for offset in range(0, 4, 2):
            rv, child = self._make_request(
                "search3",
                {"query": "a", "artistCount": 2, "artistOffset": offset},
                tag="searchResult3",
            )
            names = self._xpath(child, "./artist/@name")
            self.assertLessEqual(len(names), 2)
            for name in names:
                self.assertNotIn(name, artists)
                artists.append(name)
        self.assertSequenceEqual(
            sorted(artists), ["Clare Torry", "Miles Davis", "Various Artists"]
        )

        # paging - songs matching "e"
        rv, child = self._make_request("search3", {"query": "e"}, tag="searchResult3")
        total = len(self._xpath(child, "./song"))
        self.assertGreater(total, 2)
        songs = []
        for offset in range(0, total, 2):
            rv, child = self._make_request(
                "search3",
                {"query": "e", "songCount": 2, "songOffset": offset},
                tag="searchResult3",
            )
            elems = self._xpath(child, "./song")
            self.assertLessEqual(len(elems), 2)
            for song in map(self.__track_as_pseudo_unique_str, elems):
                self.assertNotIn(song, songs)
                songs.append(song)
        self.assertEqual(len(songs), total)

        # root filtering
        _, child = self._make_request(
            "search3", {"query": "Money", "musicFolderId": 1}, tag="searchResult3"
        )
        self.assertEqual(len(self._xpath(child, "./song")), 2)

        _, child = self._make_request(
            "search3", {"query": "Money", "musicFolderId": 2}, tag="searchResult3"
        )
        self.assertEqual(len(self._xpath(child, "./song")), 0)


if __name__ == "__main__":
    unittest.main()
