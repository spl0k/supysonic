# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import unittest

from supysonic.db import Track
from supysonic.scanner import Scanner

from ..testbase import _tool_cmd
from .apitestbase import ApiTestBase


class TranscodingTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        self._app_layer.folders.add("Folder", "tests/assets/folder")
        scanner = Scanner()
        scanner.queue_folder("Folder")
        scanner.run()

        self.trackid = Track.get().id

    def _stream(self, **kwargs):
        kwargs.update(
            {"u": "alice", "p": "Alic3", "c": "tests", "v": "1.9.0", "id": self.trackid}
        )

        rv = self.client.get("/rest/stream.view", query_string=kwargs)
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.mimetype.startswith("text/"))

        return rv

    def test_no_transcoding_available(self):
        self._make_request("stream", {"id": self.trackid, "format": "wat"}, error=0)

    def test_traversing_format_rejected(self):
        # The format ends up in the transcode cache key, which the cache resolves
        # as a file name: a format that reads as a path would have the transcoder
        # write anywhere on disk
        cache_dir = self._app_layer.transcode_cache._cache_dir
        above = os.path.dirname(cache_dir)
        before = sorted(os.listdir(above))

        for fmt in (
            "../evil",
            "../../evil",
            "..\\evil",
            "sub/dir",
            "/tmp/evil",
            "..",
            ".mp3",
            "toolongformat",
        ):
            with self.subTest(format=fmt):
                self._make_request(
                    "stream", {"id": self.trackid, "format": fmt}, error=0
                )

        self.assertEqual(sorted(os.listdir(above)), before)
        self.assertEqual(os.listdir(cache_dir), [])

    def test_traversing_format_writes_nothing(self):
        # A generic transcoder accepts any target format, so the "no way to
        # transcode" error no longer stands between the request and the write.
        # This is the deployment the documentation recommends.
        self.config.TRANSCODING["transcoder"] = _tool_cmd("echo", "pwned")

        cache_dir = self._app_layer.transcode_cache._cache_dir
        above = os.path.dirname(cache_dir)
        target = os.path.join(above, "evil")

        self._make_request(
            "stream",
            {"id": self.trackid, "format": f"..{os.sep}evil", "maxBitRate": 96},
            error=0,
        )

        self.assertFalse(os.path.exists(target))
        self.assertEqual(os.listdir(cache_dir), [])

    def test_percent_encoded_traversing_format_rejected(self):
        # Same thing, only decoded by werkzeug rather than handed over literally
        rv = self.client.get(
            "/rest/stream.view?u=alice&p=Alic3&c=tests&v=1.9.0"
            f"&id={self.trackid}&format=%2e%2e%2f%2e%2e%2fevil"
        )
        self.assertEqual(rv.mimetype, "text/xml")
        self.assertIn(b'code="0"', rv.data)

    def test_direct_transcode(self):
        rv = self._stream(maxBitRate=96, estimateContentLength="true")
        self.assertIn(os.fsencode(Track[self.trackid].path), rv.data)
        self.assertTrue(rv.data.endswith(b"96"))
        self.assertIn("Content-Length", rv.headers)
        self.assertEqual(rv.content_length, 48000)  # 4s at 96kbps

    def test_decode_encode(self):
        rv = self._stream(format="cat")
        self.assertEqual(rv.data, b"Pushing out some mp3 data...")

        rv = self._stream(format="md5")
        self.assertTrue(rv.data.startswith(b"dbb16c0847e5d8c3b1867604828cb50b"))

    def test_mostly_transcoded_cached(self):
        # See https://github.com/spl0k/supysonic/issues/202

        rv = self._stream(maxBitRate=96, estimateContentLength="true", format="rnd")

        read = 0
        it = iter(rv.response)
        # Read up to the estimated length
        while read < 48000:
            read += len(next(it))
        rv.response.close()
        rv.close()

        key = f"{self.trackid}-96.rnd"
        cache = self._app_layer.transcode_cache
        self.assertTrue(cache.has(key))
        self.assertEqual(cache.size, 52000)

    def test_partly_transcoded_cached(self):
        rv = self._stream(maxBitRate=96, estimateContentLength="true", format="rnd")

        # read one check of data then close the connection
        next(iter(rv.response))
        rv.response.close()
        rv.close()

        key = f"{self.trackid}-96.rnd"
        cache = self._app_layer.transcode_cache
        self.assertFalse(cache.has(key))
        self.assertEqual(cache.size, 0)

    def test_last_chunk_close_transcoded_cached(self):
        rv = self._stream(maxBitRate=96, estimateContentLength="true", format="rnd")

        read = 0
        it = iter(rv.response)
        # Read up to the last chunk of data but keep the generator "alive"
        while read < 52000:
            read += len(next(it))
        rv.response.close()
        rv.close()

        key = f"{self.trackid}-96.rnd"
        cache = self._app_layer.transcode_cache
        self.assertTrue(cache.has(key))
        self.assertEqual(cache.size, 52000)


if __name__ == "__main__":
    unittest.main()
