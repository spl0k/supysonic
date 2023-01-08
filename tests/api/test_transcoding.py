# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import sys

from flask import current_app

from supysonic.db import Track
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

from .apitestbase import ApiTestBase


class TranscodingTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        FolderManager.add("Folder", "tests/assets/folder")
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

    @unittest.skipIf(
        sys.platform == "win32",
        "Can't test transcoding on Windows because of a lack of simple commandline tools",
    )
    def test_direct_transcode(self):
        rv = self._stream(maxBitRate=96, estimateContentLength="true")
        self.assertIn(b"tests/assets/folder/silence.mp3", rv.data)
        self.assertTrue(rv.data.endswith(b"96"))
        self.assertIn("Content-Length", rv.headers)
        self.assertEqual(rv.content_length, 48000)  # 4s at 96kbps

    @unittest.skipIf(
        sys.platform == "win32",
        "Can't test transcoding on Windows because of a lack of simple commandline tools",
    )
    def test_decode_encode(self):
        rv = self._stream(format="cat")
        self.assertEqual(rv.data, b"Pushing out some mp3 data...")

        rv = self._stream(format="md5")
        self.assertTrue(rv.data.startswith(b"dbb16c0847e5d8c3b1867604828cb50b"))

    @unittest.skipIf(
        sys.platform == "win32",
        "Can't test transcoding on Windows because of a lack of simple commandline tools",
    )
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
        with self.app_context():
            self.assertTrue(current_app.transcode_cache.has(key))
            self.assertEqual(current_app.transcode_cache.size, 52000)

    @unittest.skipIf(
        sys.platform == "win32",
        "Can't test transcoding on Windows because of a lack of simple commandline tools",
    )
    def test_partly_transcoded_cached(self):
        rv = self._stream(maxBitRate=96, estimateContentLength="true", format="rnd")

        # read one check of data then close the connection
        next(iter(rv.response))
        rv.response.close()
        rv.close()

        key = f"{self.trackid}-96.rnd"
        with self.app_context():
            self.assertFalse(current_app.transcode_cache.has(key))
            self.assertEqual(current_app.transcode_cache.size, 0)

    @unittest.skipIf(
        sys.platform == "win32",
        "Can't test transcoding on Windows because of a lack of simple commandline tools",
    )
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
        with self.app_context():
            self.assertTrue(current_app.transcode_cache.has(key))
            self.assertEqual(current_app.transcode_cache.size, 52000)


if __name__ == "__main__":
    unittest.main()
