# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import time
import unittest
import uuid

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


class BrowseTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        self.lib = populate_library()
        self.root = self.lib.root
        self.empty_root = self.lib.empty_root

        self.assertEqual(Folder.select().count(), FOLDER_COUNT)
        self.assertEqual(Folder.select().where(Folder.root).count(), ROOT_COUNT)
        self.assertEqual(Artist.select().count(), ARTIST_COUNT)
        self.assertEqual(Album.select().count(), ALBUM_COUNT)
        self.assertEqual(Track.select().count(), TRACK_COUNT)

    def test_get_music_folders(self):
        rv, child = self._make_request("getMusicFolders", tag="musicFolders")
        self.assertEqual(len(child), 2)
        self.assertSequenceEqual(
            sorted(self._xpath(child, "./musicFolder/@name")),
            ["Empty root", "Music"],
        )

    def test_get_indexes(self):
        self._make_request("getIndexes", {"musicFolderId": "abcdef"}, error=0)
        self._make_request("getIndexes", {"musicFolderId": 1234567890}, error=70)
        self._make_request("getIndexes", {"ifModifiedSince": "quoi"}, error=0)

        rv, child = self._make_request(
            "getIndexes",
            {"ifModifiedSince": int(time.time() * 1000 + 1000)},
            tag="indexes",
        )
        self.assertEqual(len(child), 0)

        rv, child = self._make_request(
            "getIndexes", {"musicFolderId": str(self.empty_root.id)}, tag="indexes"
        )
        self.assertEqual(len(child), 0)

        # getIndexes reflects the *folder tree* (top-level folders), unlike
        # getArtists which reflects the artist tags. These now differ.
        rv, child = self._make_request("getIndexes", tag="indexes")
        self.assertEqual(len(child), 2)
        for i, (letter, name) in enumerate([("J", "Jazz"), ("R", "Rock")]):
            self.assertEqual(child[i].get("name"), letter)
            self.assertEqual(len(child[i]), 1)
            self.assertEqual(child[i][0].get("name"), name)

    def test_get_music_directory(self):
        self._make_request("getMusicDirectory", error=10)
        self._make_request("getMusicDirectory", {"id": "id"}, error=0)
        self._make_request("getMusicDirectory", {"id": 1234567890}, error=70)

        # A directory lists its child folders first (ordered by lowercased name),
        # then its tracks (ordered by sort_key).
        for f in Folder.select():
            rv, child = self._make_request(
                "getMusicDirectory", {"id": str(f.id)}, tag="directory"
            )
            self.assertEqual(child.get("id"), str(f.id))
            self.assertEqual(child.get("name"), f.name)

            folders = sorted(f.children, key=lambda c: c.name.lower())
            tracks = sorted(f.tracks, key=lambda t: t.sort_key())
            self.assertEqual(len(child), len(folders) + len(tracks))

            for dbf, xmlc in zip(folders, child[: len(folders)]):
                self.assertEqual(xmlc.get("title"), dbf.name)
                self.assertEqual(xmlc.get("isDir"), "true")
                self.assertEqual(xmlc.get("parent"), str(f.id))
            for dbt, xmlc in zip(tracks, child[len(folders) :]):
                self.assertEqual(xmlc.get("title"), dbt.title)
                self.assertEqual(xmlc.get("isDir"), "false")
                self.assertEqual(xmlc.get("parent"), str(f.id))

        # The "Rock" folder holds both a subfolder and a loose track: the folder
        # comes first, the track second.
        rock = self.lib.folders.rock
        _, child = self._make_request(
            "getMusicDirectory", {"id": str(rock.id)}, tag="directory"
        )
        self.assertEqual(len(child), 2)
        self.assertEqual(child[0].get("title"), "Dark Side")
        self.assertEqual(child[0].get("isDir"), "true")
        self.assertEqual(child[1].get("title"), "Time")
        self.assertEqual(child[1].get("isDir"), "false")

    def test_get_artists(self):
        # getArtists reflects the artist *tags*, indexed by first letter, unlike
        # getIndexes which reflects the folder tree.
        _, child = self._make_request("getArtists", tag="artists")
        self.assertEqual(len(child), 4)
        expected = [
            ("C", "Clare Torry"),
            ("M", "Miles Davis"),
            ("P", "Pink Floyd"),
            ("V", "Various Artists"),
        ]
        for i, (letter, name) in enumerate(expected):
            self.assertEqual(child[i].get("name"), letter)
            self.assertEqual(len(child[i]), 1)
            self.assertEqual(child[i][0].get("name"), name)

        self._make_request("getArtists", {"musicFolderId": "id"}, error=0)
        self._make_request("getArtists", {"musicFolderId": -3}, error=70)

        _, child = self._make_request(
            "getArtists", {"musicFolderId": str(self.empty_root.id)}, tag="artists"
        )
        self.assertEqual(len(child), 0)

        # Filtering by root joins on tracks, so "Various Artists" (which owns an
        # album but has no tracks of its own) drops out: C, M, P only.
        _, child = self._make_request(
            "getArtists", {"musicFolderId": str(self.root.id)}, tag="artists"
        )
        self.assertEqual(len(child), 3)
        self.assertSequenceEqual(
            [idx.get("name") for idx in child], ["C", "M", "P"]
        )

    def test_get_artist(self):
        self._make_request("getArtist", error=10)
        self._make_request("getArtist", {"id": "artist"}, error=0)
        self._make_request("getArtist", {"id": str(uuid.uuid4())}, error=70)

        # Clare Torry owns no album, but is a guest on one (The Dark Side of the
        # Moon). getArtist surfaces that album via her track, and the album's
        # artist is *not* her.
        torry = self.lib.artists.clare_torry
        _, child = self._make_request("getArtist", {"id": str(torry.id)}, tag="artist")
        self.assertEqual(child.get("id"), str(torry.id))
        self.assertEqual(child.get("albumCount"), "0")
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("name"), "The Dark Side of the Moon")
        self.assertEqual(child[0].get("artist"), "Pink Floyd")

        # Pink Floyd owns one album but appears on two (the union with the
        # compilation reached through "Money (Live)"). albumCount counts owned
        # albums only, so it differs from the number of returned albums.
        floyd = self.lib.artists.pink_floyd
        _, child = self._make_request("getArtist", {"id": str(floyd.id)}, tag="artist")
        self.assertEqual(child.get("albumCount"), "1")
        self.assertEqual(len(child), 2)
        self.assertSequenceEqual(
            sorted(a.get("name") for a in child),
            ["Greatest Jazz Hits", "The Dark Side of the Moon"],
        )

    def test_get_album(self):
        self._make_request("getAlbum", error=10)
        self._make_request("getAlbum", {"id": "nastynasty"}, error=0)
        self._make_request("getAlbum", {"id": str(uuid.uuid4())}, error=70)

        # The compilation: every song's artist differs from the album's artist.
        a = self.lib.albums.greatest
        rv, child = self._make_request("getAlbum", {"id": str(a.id)}, tag="album")
        self.assertEqual(child.get("id"), str(a.id))
        self.assertEqual(child.get("artist"), "Various Artists")
        self.assertEqual(child.get("songCount"), str(len(child)))
        self.assertEqual(len(child), a.tracks.count())
        for xal in child:
            self.assertEqual(xal.get("album"), a.name)
            self.assertEqual(xal.get("albumId"), str(a.id))
            self.assertNotEqual(xal.get("artist"), child.get("artist"))

    def test_get_song(self):
        self._make_request("getSong", error=10)
        self._make_request("getSong", {"id": "nastynasty"}, error=0)
        self._make_request("getSong", {"id": str(uuid.uuid4())}, error=70)

        s = Track.select().first()
        self._make_request("getSong", {"id": str(s.id)}, tag="song")

    def test_get_videos(self):
        self._make_request("getVideos", error=0)

    def test_genres(self):
        rv, child = self._make_request("getGenres", tag="genres")
        self.assertEqual(len(child), 2)

        genres = {g.text: g for g in child}
        self.assertEqual(set(genres), {"Rock", "Jazz"})
        # Rock: 5 songs across 2 albums (Dark Side + the compilation)
        self.assertEqual(genres["Rock"].get("songCount"), "5")
        self.assertEqual(genres["Rock"].get("albumCount"), "2")
        # Jazz: 2 songs across 2 albums (Kind of Blue + the compilation)
        self.assertEqual(genres["Jazz"].get("songCount"), "2")
        self.assertEqual(genres["Jazz"].get("albumCount"), "2")
        # "Blue in Green" has a null genre and is excluded entirely.


if __name__ == "__main__":
    unittest.main()
