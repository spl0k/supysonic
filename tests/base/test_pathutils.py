# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest

from supysonic.pathutils import is_subpath


# Written with forward slashes for readability, turned into whatever the
# platform uses so the tests actually exercise the local separator.
def _p(path):
    return path.replace("/", os.sep)


class IsSubpathTestCase(unittest.TestCase):
    def assertSubpath(self, path, parent):
        self.assertTrue(
            is_subpath(_p(path), _p(parent)), f"{path} should be inside {parent}"
        )

    def assertNotSubpath(self, path, parent):
        self.assertFalse(
            is_subpath(_p(path), _p(parent)), f"{path} shouldn't be inside {parent}"
        )

    def test_below(self):
        self.assertSubpath("/music/rock/track.mp3", "/music")
        self.assertSubpath("/music/rock", "/music")

    def test_itself(self):
        self.assertSubpath("/music", "/music")
        self.assertSubpath("/music", "/music/")
        self.assertSubpath("/music/", "/music")

    def test_sharing_a_prefix(self):
        # The whole point: a string prefix isn't a path prefix
        self.assertNotSubpath("/music2", "/music")
        self.assertNotSubpath("/music-backup/track.mp3", "/music")
        self.assertNotSubpath("/music/rockabilly/track.mp3", "/music/rock")

    def test_unrelated(self):
        self.assertNotSubpath("/videos/movie.mkv", "/music")
        self.assertNotSubpath("/music", "/music/rock")

    def test_trailing_separators(self):
        self.assertSubpath("/music/rock/track.mp3", "/music/")
        self.assertNotSubpath("/music2/track.mp3", "/music/")

    def test_filesystem_root(self):
        # the root's prefix mustn't end up doubled ("//")
        self.assertTrue(is_subpath(_p("/music"), os.sep))


if __name__ == "__main__":
    unittest.main()
