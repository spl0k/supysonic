#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import flask.json
import os.path
import requests

from pony.orm import db_session

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase


class LyricsTestCase(ApiTestBase):
    def setUp(self):
        super(LyricsTestCase, self).setUp()

        with db_session:
            folder = Folder(
                name="Root",
                path=os.path.abspath("tests/assets"),
                root=True,
                cover_art="cover.jpg",
            )
            self.folderid = folder.id

            artist = Artist(name="Artist")
            album = Album(artist=artist, name="Album")

            track = Track(
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

    def test_get_lyrics(self):
        self._make_request("getLyrics", error=10)
        self._make_request("getLyrics", {"artist": "artist"}, error=10)
        self._make_request("getLyrics", {"title": "title"}, error=10)

        # Potentially skip the tests if ChartLyrics is down (which happens quite often)
        try:
            requests.get("http://api.chartlyrics.com/", timeout=5)
        except requests.exceptions.Timeout:
            self.skipTest("ChartLyrics down")

        rv, child = self._make_request(
            "getLyrics",
            {
                "artist": "some really long name hoping",
                "title": "to get absolutely no result",
            },
            tag="lyrics",
        )
        self.assertIsNone(child.text)

        # ChartLyrics
        rv, child = self._make_request(
            "getLyrics",
            {"artist": "The Clash", "title": "London Calling"},
            tag="lyrics",
        )
        self.assertIn("live by the river", child.text)
        # ChartLyrics, JSON format
        args = {
            "u": "alice",
            "p": "Alic3",
            "c": "tests",
            "f": "json",
            "artist": "The Clash",
            "title": "London Calling",
        }
        rv = self.client.get("/rest/getLyrics.view", query_string=args)
        json = flask.json.loads(rv.data)
        self.assertIn("value", json["subsonic-response"]["lyrics"])
        self.assertIn("live by the river", json["subsonic-response"]["lyrics"]["value"])

        # Local file
        rv, child = self._make_request(
            "getLyrics", {"artist": "artist", "title": "23bytes"}, tag="lyrics"
        )
        self.assertIn("null", child.text)


if __name__ == "__main__":
    unittest.main()
