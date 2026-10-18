# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import tempfile
import unittest
import zipfile
from contextlib import closing
from io import BytesIO

from PIL import Image

from supysonic.db.models import Album, Artist, Folder, Track

from ..api.apitestbase import ApiTestBase
from . import fakes, silent

NO_ART = os.path.abspath("tests/assets/23bytes")


class CoverArtProvidersTestCase(ApiTestBase):
    """Checks serialization and getCoverArt ask the loaded providers.

    Uses fake providers rather than real ones so it stays about the plumbing:
    the library has no cover of its own to find, neither files nor embedded.
    """

    __sections__ = {
        "webapp": {"cover_art_providers": f"{silent.__name__} {fakes.__name__}"}
    }

    def setUp(self):
        super().setUp()

        self.silent, self.fake = self._app_layer.cover_art_providers

        self.folder = Folder.create(name="Root", path=tempfile.gettempdir(), root=True)
        artist = Artist.create(name="Artist")
        self.album = Album.create(artist=artist, name="Album")
        self.track = Track.create(
            title="Track",
            number=1,
            disc=1,
            artist=artist,
            album=self.album,
            path=NO_ART,
            root_folder=self.folder,
            folder=self.folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

        self.fid = str(self.folder.id)
        self.aid = str(self.album.id)
        self.tid = str(self.track.id)

    def _get(self, endpoint, **args):
        args.update(u="alice", p="Alic3", c="tests")
        return closing(self.client.get(f"/rest/{endpoint}.view", query_string=args))

    def _song_cover(self):
        rv, child = self._make_request("getSong", {"id": self.tid}, tag="song")
        return child.get("coverArt")

    def test_nothing_announced(self):
        self.assertIsNone(self._song_cover())

    def test_announced_cover(self):
        self.fake.announces = {self.tid: self.fid}

        self.assertEqual(self._song_cover(), self.fid)

    def test_providers_are_asked_in_order(self):
        self.silent.announces = {self.tid: self.fid}
        self.fake.announces = {self.tid: self.aid}

        self.assertEqual(self._song_cover(), self.fid)

    def test_own_cover_is_preferred(self):
        self.silent.announces = {self.tid: self.fid}
        self.fake.announces = {self.tid: self.tid}

        self.assertEqual(self._song_cover(), self.tid)

    def test_folders_and_albums_are_announced(self):
        self.fake.announces = {self.fid: self.tid, self.aid: self.tid}

        rv, child = self._make_request(
            "getAlbumList", {"type": "newest"}, tag="albumList"
        )
        self.assertEqual(self._xpath(child, "./album")[0].get("coverArt"), self.tid)

        rv, child = self._make_request(
            "getAlbumList2", {"type": "newest"}, tag="albumList2"
        )
        self.assertEqual(self._xpath(child, "./album")[0].get("coverArt"), self.tid)

    def test_get_cover_art(self):
        self.fake.covers = {self.tid: fakes.cover()}

        with self._get("getCoverArt", id=self.tid) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, "image/png")
            self.assertEqual(rv.data, fakes.png())

        self.assertEqual(self.silent.served, [self.tid])
        self.assertEqual(self.fake.served, [self.tid])

    def test_get_cover_art_resized(self):
        self.fake.covers = {self.fid: fakes.cover(64)}

        for _ in range(2):  # Second time from the cache
            with self._get("getCoverArt", id=self.fid, size=16) as rv:
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.mimetype, "image/png")
                with Image.open(BytesIO(rv.data)) as im:
                    self.assertEqual(im.size, (16, 16))

    def test_get_cover_art_not_upscaled(self):
        self.fake.covers = {self.aid: fakes.cover(16)}

        with self._get("getCoverArt", id=self.aid, size=64) as rv:
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.data, fakes.png(16))

    def test_get_cover_art_first_answer_wins(self):
        self.silent.covers = {self.tid: fakes.cover(16)}
        self.fake.covers = {self.tid: fakes.cover()}

        with self._get("getCoverArt", id=self.tid) as rv:
            self.assertEqual(rv.data, fakes.png(16))

        self.assertEqual(self.fake.served, [])

    def test_get_cover_art_nobody_answers(self):
        self._make_request("getCoverArt", {"id": self.tid}, error=70)
        self._make_request("getCoverArt", {"id": self.aid}, error=70)
        self._make_request("getCoverArt", {"id": self.fid}, error=70)

    def test_get_cover_art_only_serves_own_covers(self):
        # Only the id it was announced with leads to a fallback cover
        self.fake.announces = {self.aid: self.fid}
        self.fake.covers = {self.fid: fakes.cover()}

        self._make_request("getCoverArt", {"id": self.aid}, error=70)

    def _download_album(self):
        with self._get("download", id=self.aid) as rv:
            self.assertEqual(rv.status_code, 200)
            with zipfile.ZipFile(BytesIO(rv.data)) as z:
                return {name: z.read(name) for name in z.namelist()}

    def test_download_album_with_cover(self):
        self.fake.announces = {self.aid: self.fid}
        self.fake.covers = {self.fid: fakes.cover()}

        files = self._download_album()

        self.assertEqual(files["cover.png"], fakes.png())
        self.assertIn("23bytes", files)

    def test_download_album_with_track_cover(self):
        # The cover is embedded in the track, which is already in there
        self.fake.announces = {self.aid: self.tid}
        self.fake.covers = {self.tid: fakes.cover()}

        self.assertEqual(list(self._download_album()), ["23bytes"])
        self.assertEqual(self.fake.served, [])

    def test_download_album_without_cover(self):
        self.assertEqual(list(self._download_album()), ["23bytes"])


if __name__ == "__main__":
    unittest.main()
