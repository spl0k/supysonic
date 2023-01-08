# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest
import uuid

from contextlib import closing
from io import BytesIO
from PIL import Image

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase


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

    def test_get_avatar(self):
        self._make_request("getAvatar", error=0)


if __name__ == "__main__":
    unittest.main()
