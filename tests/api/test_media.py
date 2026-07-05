# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import os.path
import shutil
import tempfile
import unittest
import uuid

from contextlib import closing
from io import BytesIO
from PIL import Image

from supysonic.db import Folder, Artist, Album, Track, User, ClientPrefs

from .apitestbase import ApiTestBase

SILENCE_MP3 = os.path.abspath("tests/assets/formats/silence.mp3")


class MediaTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        folder = Folder.create(
            name="Root",
            path=os.path.abspath("tests/assets"),
            root=True,
            cover_art="cover.jpg",
        )
        folder = Folder.get(name="Root")
        self.folderid = folder.id

        artist = Artist.create(name="Artist")
        album = Album.create(artist=artist, name="Album")

        track = Track.create(
            title="23bytes",
            number=1,
            disc=1,
            artist=artist,
            album=album,
            path=os.path.abspath("tests/assets/23bytes"),
            root_folder=folder,
            folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )
        self.trackid = track.id

        self.formats = ["mp3", "flac", "ogg", "m4a"]
        for i in range(len(self.formats)):
            track_embeded_art = Track.create(
                title="[silence]",
                number=1,
                disc=1,
                artist=artist,
                album=album,
                path=os.path.abspath(f"tests/assets/formats/silence.{self.formats[i]}"),
                root_folder=folder,
                folder=folder,
                duration=2,
                bitrate=320,
                last_modification=0,
            )
            self.formats[i] = track_embeded_art.id

    def test_stream(self):
        self._make_request("stream", error=10)
        self._make_request("stream", {"id": "string"}, error=0)
        self._make_request("stream", {"id": str(uuid.uuid4())}, error=70)
        self._make_request("stream", {"id": str(self.folderid)}, error=0)
        self._make_request(
            "stream", {"id": str(self.trackid), "maxBitRate": "string"}, error=0
        )
        self._make_request(
            "stream", {"id": str(self.trackid), "timeOffset": 2}, error=0
        )
        self._make_request(
            "stream", {"id": str(self.trackid), "size": "640x480"}, error=0
        )

        with closing(
            self.client.get(
                "/rest/stream.view",
                query_string={
                    "u": "alice",
                    "p": "Alic3",
                    "c": "tests",
                    "id": str(self.trackid),
                },
            )
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(len(rv.data), 23)
        self.assertEqual(Track[self.trackid].play_count, 1)

    def test_download(self):
        self._make_request("download", error=10)
        self._make_request("download", {"id": "string"}, error=0)
        self._make_request("download", {"id": str(uuid.uuid4())}, error=70)
        # Integer id parses as a (nonexistent) folder rather than a track/album
        self._make_request("download", {"id": "1234567890"}, error=70)

        # download single file
        with closing(
            self.client.get(
                "/rest/download.view",
                query_string={
                    "u": "alice",
                    "p": "Alic3",
                    "c": "tests",
                    "id": str(self.trackid),
                },
            )
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(len(rv.data), 23)
        self.assertEqual(Track[self.trackid].play_count, 0)

        # dowload folder
        rv = self.client.get(
            "/rest/download.view",
            query_string={
                "u": "alice",
                "p": "Alic3",
                "c": "tests",
                "id": str(self.folderid),
            },
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, "application/zip")

    def __assert_image_data(self, resp, format, size):
        with Image.open(BytesIO(resp.data)) as im:
            self.assertEqual(im.format, format)
            self.assertEqual(im.size, (size, size))

    def test_get_cover_art(self):
        self._make_request("getCoverArt", error=10)
        self._make_request("getCoverArt", {"id": "string"}, error=0)
        self._make_request("getCoverArt", {"id": str(uuid.uuid4())}, error=70)
        self._make_request("getCoverArt", {"id": str(self.trackid)}, error=70)
        self._make_request(
            "getCoverArt", {"id": str(self.folderid), "size": "large"}, error=0
        )

        args = {"u": "alice", "p": "Alic3", "c": "tests", "id": str(self.folderid)}
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/jpeg")
            self.__assert_image_data(rv, "JPEG", 420)

        args["size"] = 600
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/jpeg")
            self.__assert_image_data(rv, "JPEG", 420)

        args["size"] = 120
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/jpeg")
            self.__assert_image_data(rv, "JPEG", 120)

        # rerequest, just in case
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/jpeg")
            self.__assert_image_data(rv, "JPEG", 120)

        # TODO test non square covers

        # Test extracting cover art from embeded media
        for args["id"] in self.formats:
            with closing(
                self.client.get("/rest/getCoverArt.view", query_string=args)
            ) as rv:
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.mimetype, "image/png")
                self.__assert_image_data(rv, "PNG", 120)

    def test_stream_client_prefs(self):
        # Client preferences drive the destination format/bitrate when the
        # request doesn't specify them. A lower preferred bitrate forces
        # transcoding (mp3 -> mp3 @128) through the test transcoder.
        alice = User.get(name="alice")
        ClientPrefs.create(
            user=alice, client_name="tests", format="mp3", bitrate=128
        )

        with closing(
            self.client.get(
                "/rest/stream.view",
                query_string={
                    "u": "alice",
                    "p": "Alic3",
                    "c": "tests",
                    "id": str(self.formats[0]),  # silence.mp3
                },
            )
        ) as rv:
            self.assertEqual(rv.status_code, 200)

    def test_download_album(self):
        # An album download zips its tracks. Two tracks sharing a basename
        # exercise the collision-avoidance suffixing, and the album's folder
        # cover art is appended to the archive.
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        os.mkdir(os.path.join(d, "a"))
        os.mkdir(os.path.join(d, "b"))
        p1 = os.path.join(d, "a", "song.mp3")
        p2 = os.path.join(d, "b", "song.mp3")
        shutil.copyfile(SILENCE_MP3, p1)
        shutil.copyfile(SILENCE_MP3, p2)

        root = Folder.get(name="Root")  # cover_art="cover.jpg", path=tests/assets
        artist = Artist.get()
        album = Album.create(artist=artist, name="Zip me")
        for p in (p1, p2):
            Track.create(
                title=os.path.basename(p),
                number=1,
                disc=1,
                artist=artist,
                album=album,
                path=p,
                root_folder=root,
                folder=root,
                duration=2,
                bitrate=320,
                last_modification=0,
            )

        rv = self.client.get(
            "/rest/download.view",
            query_string={
                "u": "alice",
                "p": "Alic3",
                "c": "tests",
                "id": str(album.id),
            },
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, "application/zip")

    def test_download_empty_album(self):
        # An album with no tracks (and no cover) yields an empty archive.
        album = Album.create(artist=Artist.get(), name="Empty")
        self._make_request("download", {"id": str(album.id)}, error=0)

    def test_get_cover_art_collections(self):
        # Album cover resolved from a track's folder cover art (Root/cover.jpg)
        album = Album.get()
        args = {"u": "alice", "p": "Alic3", "c": "tests", "id": str(album.id)}
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/jpeg")

        # Album cover extracted from embedded art when no folder has cover art.
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        embedded_path = os.path.join(d, "silence.mp3")
        shutil.copyfile(SILENCE_MP3, embedded_path)
        root = Folder.get(name="Root")
        nocover = Folder.create(
            name="NoCover", root=False, path=d, parent=root
        )
        artist = Artist.get()
        embedded_album = Album.create(artist=artist, name="Embedded")
        Track.create(
            title="embedded",
            number=1,
            disc=1,
            artist=artist,
            album=embedded_album,
            path=embedded_path,
            root_folder=root,
            folder=nocover,
            duration=2,
            bitrate=320,
            has_art=True,
            last_modification=0,
        )
        args["id"] = str(embedded_album.id)
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/png")

        # A track's extracted cover has no image extension, so with no size
        # the mimetype is derived from the image contents.
        args["id"] = str(self.formats[0])
        args.pop("size", None)
        with closing(
            self.client.get("/rest/getCoverArt.view", query_string=args)
        ) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/png")

    def test_get_cover_art_missing(self):
        # A folder whose cover_art points at a missing file yields no cover.
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        badfolder = Folder.create(
            name="Bad",
            root=True,
            path=d,
            cover_art="nonexistent.jpg",
        )
        self._make_request("getCoverArt", {"id": str(badfolder.id)}, error=70)

        # An integer id parsing as a nonexistent folder falls through to "not
        # found" rather than raising.
        self._make_request("getCoverArt", {"id": "1234567890"}, error=70)

    def test_get_avatar(self):
        self._make_request("getAvatar", error=0)


if __name__ == "__main__":
    unittest.main()
