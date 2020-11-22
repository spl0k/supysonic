# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import unittest
import shutil
import time
import tempfile

from supysonic.cache import Cache, CacheMiss, ProtectedError


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.__dir)

    def test_existing_files_order(self):
        cache = Cache(self.__dir, 30)
        val = b"0123456789"
        cache.set("key1", val)
        cache.set("key2", val)
        cache.set("key3", val)
        self.assertEqual(cache.size, 30)

        # file mtime is accurate to the second
        time.sleep(1)
        cache.get_value("key1")

        cache = Cache(self.__dir, 30, min_time=0)
        self.assertEqual(cache.size, 30)
        self.assertTrue(cache.has("key1"))
        self.assertTrue(cache.has("key2"))
        self.assertTrue(cache.has("key3"))

        cache.set("key4", val)
        self.assertEqual(cache.size, 30)
        self.assertTrue(cache.has("key1"))
        self.assertFalse(cache.has("key2"))
        self.assertTrue(cache.has("key3"))
        self.assertTrue(cache.has("key4"))

    def test_missing(self):
        cache = Cache(self.__dir, 10)
        self.assertFalse(cache.has("missing"))
        with self.assertRaises(CacheMiss):
            cache.get_value("missing")

    def test_delete_missing(self):
        cache = Cache(self.__dir, 0, min_time=0)
        cache.delete("missing1")
        cache.delete("missing2")

    def test_store_literal(self):
        cache = Cache(self.__dir, 10)
        val = b"0123456789"
        cache.set("key", val)
        self.assertEqual(cache.size, 10)
        self.assertTrue(cache.has("key"))
        self.assertEqual(cache.get_value("key"), val)

    def test_store_generated(self):
        cache = Cache(self.__dir, 10)
        val = [b"0", b"12", b"345", b"6789"]

        def gen():
            yield from val

        t = []
        for x in cache.set_generated("key", gen):
            t.append(x)
            self.assertEqual(cache.size, 0)
            self.assertFalse(cache.has("key"))

        self.assertEqual(t, val)
        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key"), b"".join(val))

    def test_store_to_fp(self):
        cache = Cache(self.__dir, 10)
        val = b"0123456789"
        with cache.set_fileobj("key") as fp:
            fp.write(val)
            self.assertEqual(cache.size, 0)

        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key"), val)

    def test_access_data(self):
        cache = Cache(self.__dir, 25, min_time=0)
        val = b"0123456789"
        cache.set("key", val)

        self.assertEqual(cache.get_value("key"), val)

        with cache.get_fileobj("key") as f:
            self.assertEqual(f.read(), val)

        with open(cache.get("key"), "rb") as f:
            self.assertEqual(f.read(), val)

    def test_accessing_preserves(self):
        cache = Cache(self.__dir, 25, min_time=0)
        val = b"0123456789"
        cache.set("key1", val)
        cache.set("key2", val)
        self.assertEqual(cache.size, 20)

        cache.get_value("key1")

        cache.set("key3", val)
        self.assertEqual(cache.size, 20)
        self.assertTrue(cache.has("key1"))
        self.assertFalse(cache.has("key2"))
        self.assertTrue(cache.has("key3"))

    def test_automatic_delete_oldest(self):
        cache = Cache(self.__dir, 25, min_time=0)
        val = b"0123456789"
        cache.set("key1", val)
        self.assertTrue(cache.has("key1"))
        self.assertEqual(cache.size, 10)

        cache.set("key2", val)
        self.assertEqual(cache.size, 20)
        self.assertTrue(cache.has("key1"))
        self.assertTrue(cache.has("key2"))

        cache.set("key3", val)
        self.assertEqual(cache.size, 20)
        self.assertFalse(cache.has("key1"))
        self.assertTrue(cache.has("key2"))
        self.assertTrue(cache.has("key3"))

    def test_delete(self):
        cache = Cache(self.__dir, 25, min_time=0)
        val = b"0123456789"
        cache.set("key1", val)
        self.assertTrue(cache.has("key1"))
        self.assertEqual(cache.size, 10)

        cache.delete("key1")

        self.assertFalse(cache.has("key1"))
        self.assertEqual(cache.size, 0)

    def test_cleanup_on_error(self):
        cache = Cache(self.__dir, 10)

        def gen():
            # Cause a TypeError halfway through
            yield from [b"0", b"12", object(), b"345", b"6789"]

        with self.assertRaises(TypeError):
            for x in cache.set_generated("key", gen):
                pass

        # Make sure no partial files are left after the error
        self.assertEqual(list(os.listdir(self.__dir)), list())

    def test_parallel_generation(self):
        cache = Cache(self.__dir, 20)

        def gen():
            yield from [b"0", b"12", b"345", b"6789"]

        g1 = cache.set_generated("key", gen)
        g2 = cache.set_generated("key", gen)

        next(g1)
        files = os.listdir(self.__dir)
        self.assertEqual(len(files), 1)
        for x in files:
            self.assertTrue(x.endswith(".part"))

        next(g2)
        files = os.listdir(self.__dir)
        self.assertEqual(len(files), 2)
        for x in files:
            self.assertTrue(x.endswith(".part"))

        self.assertEqual(cache.size, 0)
        for x in g1:
            pass
        self.assertEqual(cache.size, 10)
        self.assertTrue(cache.has("key"))

        # Replace the file - size should stay the same
        for x in g2:
            pass
        self.assertEqual(cache.size, 10)
        self.assertTrue(cache.has("key"))

        # Only a single file
        self.assertEqual(len(os.listdir(self.__dir)), 1)

    def test_replace(self):
        cache = Cache(self.__dir, 20)
        val_small = b"0"
        val_big = b"0123456789"

        cache.set("key", val_small)
        self.assertEqual(cache.size, 1)

        cache.set("key", val_big)
        self.assertEqual(cache.size, 10)

        cache.set("key", val_small)
        self.assertEqual(cache.size, 1)

    def test_no_auto_prune(self):
        cache = Cache(self.__dir, 10, min_time=0, auto_prune=False)
        val = b"0123456789"

        cache.set("key1", val)
        cache.set("key2", val)
        cache.set("key3", val)
        cache.set("key4", val)
        self.assertEqual(cache.size, 40)
        cache.prune()

        self.assertEqual(cache.size, 10)

    def test_min_time_clear(self):
        cache = Cache(self.__dir, 40, min_time=1)
        val = b"0123456789"

        cache.set("key1", val)
        cache.set("key2", val)
        time.sleep(1)
        cache.set("key3", val)
        cache.set("key4", val)

        self.assertEqual(cache.size, 40)
        cache.clear()
        self.assertEqual(cache.size, 20)
        time.sleep(1)
        cache.clear()
        self.assertEqual(cache.size, 0)

    def test_not_expired(self):
        cache = Cache(self.__dir, 40, min_time=1)
        val = b"0123456789"
        cache.set("key1", val)
        with self.assertRaises(ProtectedError):
            cache.delete("key1")
        time.sleep(1)
        cache.delete("key1")
        self.assertEqual(cache.size, 0)

    def test_missing_cache_file(self):
        cache = Cache(self.__dir, 10, min_time=0)
        val = b"0123456789"
        os.remove(cache.set("key", val))

        self.assertEqual(cache.size, 10)
        self.assertFalse(cache.has("key"))
        self.assertEqual(cache.size, 0)

        os.remove(cache.set("key", val))
        self.assertEqual(cache.size, 10)
        with self.assertRaises(CacheMiss):
            cache.get("key")
        self.assertEqual(cache.size, 0)


if __name__ == "__main__":
    unittest.main()
