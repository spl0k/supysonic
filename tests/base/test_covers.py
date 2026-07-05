# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import shutil
import tempfile
import unittest

from supysonic.covers import CoverFile, find_cover_in_folder, is_valid_cover

COVER = os.path.abspath("tests/assets/cover.jpg")


class CoversTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def __copy_cover(self, name):
        dest = os.path.join(self.dir, name)
        shutil.copyfile(COVER, dest)
        return dest

    def test_score_naming_rules(self):
        self.assertEqual(CoverFile("randomname.jpg").score, 0)
        self.assertEqual(CoverFile("cover.jpg").score, 5)
        self.assertEqual(CoverFile("front.png").score, 10)
        self.assertEqual(CoverFile("back.jpg").score, -10)
        # multiple rules stack
        self.assertEqual(CoverFile("cover-large.jpg").score, 7)

    def test_score_album_name_match(self):
        # a filename matching the album name earns the +20 bonus
        self.assertEqual(CoverFile("Some Album.jpg", "Some Album").score, 20)
        # matching is done on the cleaned (letters-only, lowercased) names
        self.assertEqual(CoverFile("some_album!.jpg", "Some Album").score, 20)
        # cover.jpg bonus (5) plus the album-name match (20)
        self.assertEqual(CoverFile("cover.jpg", "cover").score, 25)
        # no relation between the names: only the naming rule applies
        self.assertEqual(CoverFile("front.jpg", "Totally Different").score, 10)

    def test_is_valid_cover(self):
        self.assertTrue(is_valid_cover(COVER))
        # not a file
        self.assertFalse(is_valid_cover(self.dir))
        self.assertFalse(is_valid_cover(os.path.join(self.dir, "nope.jpg")))
        # wrong extension
        txt = os.path.join(self.dir, "notimage.txt")
        with open(txt, "w") as f:
            f.write("hello")
        self.assertFalse(is_valid_cover(txt))
        # image extension but unreadable content
        corrupt = os.path.join(self.dir, "corrupt.jpg")
        with open(corrupt, "wb") as f:
            f.write(b"this is definitely not a valid image")
        self.assertFalse(is_valid_cover(corrupt))

    def test_find_cover_invalid_path(self):
        self.assertRaises(
            ValueError, find_cover_in_folder, os.path.join(self.dir, "nonexistent")
        )

    def test_find_cover_empty_folder(self):
        self.assertIsNone(find_cover_in_folder(self.dir))

    def test_find_cover_single_candidate(self):
        self.__copy_cover("whatever.jpg")
        cover = find_cover_in_folder(self.dir)
        self.assertIsNotNone(cover)
        self.assertEqual(cover.name, "whatever.jpg")

    def test_find_cover_picks_best_score(self):
        # An invalid file is ignored; the highest-scoring valid one wins.
        self.__copy_cover("back.jpg")  # score -10
        self.__copy_cover("folder.jpg")  # score 5
        self.__copy_cover("front.jpg")  # score 10
        with open(os.path.join(self.dir, "bogus.jpg"), "wb") as f:
            f.write(b"not an image")

        cover = find_cover_in_folder(self.dir)
        self.assertEqual(cover.name, "front.jpg")

    def test_find_cover_album_name_beats_naming(self):
        # The album-name match (+20) outweighs the "front" naming rule (+10).
        self.__copy_cover("front.jpg")  # score 10
        self.__copy_cover("Greatest Hits.jpg")  # score 20 with album match

        cover = find_cover_in_folder(self.dir, "Greatest Hits")
        self.assertEqual(cover.name, "Greatest Hits.jpg")


if __name__ == "__main__":
    unittest.main()
