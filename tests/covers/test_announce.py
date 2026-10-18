# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
from types import SimpleNamespace

from supysonic.covers import announce_covers

from .fakes import FakeProvider
from .silent import SilentProvider


def _entities(*ids):
    return [SimpleNamespace(id=eid) for eid in ids]


class AnnounceCoversTestCase(unittest.TestCase):
    def setUp(self):
        self.first = SilentProvider(None)
        self.second = FakeProvider(None)
        self.providers = [self.first, self.second]

    def test_no_providers(self):
        self.assertEqual(announce_covers([], _entities("a", "b")), {})

    def test_no_entities(self):
        self.assertEqual(announce_covers(self.providers, []), {})
        self.assertEqual(self.first.asked, [])

    def test_nobody_announces(self):
        self.assertEqual(announce_covers(self.providers, _entities("a")), {})

    def test_own_cover(self):
        self.second.announces = {"a": "a"}

        self.assertEqual(
            announce_covers(self.providers, _entities("a", "b")), {"a": "a"}
        )

    def test_fallback_cover(self):
        self.second.announces = {"a": "parent"}

        self.assertEqual(
            announce_covers(self.providers, _entities("a")), {"a": "parent"}
        )

    def test_own_beats_fallback_whatever_the_order(self):
        self.first.announces = {"a": "parent"}
        self.second.announces = {"a": "a"}

        self.assertEqual(announce_covers(self.providers, _entities("a")), {"a": "a"})

    def test_first_own_wins(self):
        self.first.announces = {"a": "a"}
        self.second.announces = {"a": "a"}

        announce_covers(self.providers, _entities("a"))

        # Not even asked
        self.assertEqual(self.second.asked, [])

    def test_first_fallback_wins(self):
        self.first.announces = {"a": "parent"}
        self.second.announces = {"a": "grandparent"}

        self.assertEqual(
            announce_covers(self.providers, _entities("a")), {"a": "parent"}
        )

    def test_owned_entities_arent_passed_on(self):
        self.first.announces = {"a": "a", "b": "parent"}

        announce_covers(self.providers, _entities("a", "b", "c"))

        self.assertEqual(self.first.asked, [["a", "b", "c"]])
        self.assertEqual(self.second.asked, [["b", "c"]])

    def test_ids_are_strings(self):
        self.second.announces = {"1": 2}

        self.assertEqual(announce_covers(self.providers, _entities(1)), {"1": "2"})

    def test_unasked_entities_are_ignored(self):
        self.second.find_covers = lambda entities: {"z": "z"}

        self.assertEqual(announce_covers(self.providers, _entities("a")), {})


if __name__ == "__main__":
    unittest.main()
