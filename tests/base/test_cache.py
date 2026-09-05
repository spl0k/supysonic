# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2026 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

import errno
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from supysonic.cache import Cache, CacheMiss, ProtectedError


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.__dir)

    def test_makedirs_error_propagates(self):
        # An error other than "already exists" while creating the cache dir
        # must not be swallowed.
        with patch("os.makedirs", side_effect=OSError(errno.EACCES, "denied")):
            self.assertRaises(OSError, Cache, self.__dir, 30)

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

    def __missing_dir(self):
        """Build a cache whose directory got removed behind its back

        Happens when the cache lives under a directory subject to OS cleanup,
        /tmp being the default. Returns the (gone) cache dir and the cache.
        """
        cache_dir = os.path.join(self.__dir, "sub", "cache")
        cache = Cache(cache_dir, 30, min_time=0)
        shutil.rmtree(os.path.join(self.__dir, "sub"))
        self.assertFalse(os.path.exists(cache_dir))
        return cache_dir, cache

    def test_missing_cache_dir_literal(self):
        cache_dir, cache = self.__missing_dir()
        val = b"0123456789"

        cache.set("key", val)

        self.assertTrue(os.path.isdir(cache_dir))
        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key"), val)

    def test_missing_cache_dir_fileobj(self):
        cache_dir, cache = self.__missing_dir()
        val = b"0123456789"

        with cache.set_fileobj("key") as fp:
            fp.write(val)

        self.assertTrue(os.path.isdir(cache_dir))
        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key"), val)

    def test_missing_cache_dir_generated(self):
        cache_dir, cache = self.__missing_dir()
        val = [b"0", b"12", b"345", b"6789"]

        def gen():
            yield from val

        self.assertEqual(list(cache.set_generated("key", gen)), val)

        self.assertTrue(os.path.isdir(cache_dir))
        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key"), b"".join(val))

    def test_missing_cache_dir_bookkeeping(self):
        # Losing the directory leaves the in-memory map stale. It heals, but
        # lazily: only the entries that get looked at are reclaimed.
        cache_dir = os.path.join(self.__dir, "sub", "cache")
        cache = Cache(cache_dir, 30, min_time=0)
        val = b"0123456789"
        cache.set("key1", val)
        cache.set("key2", val)
        cache.set("key3", val)
        self.assertEqual(cache.size, 30)

        shutil.rmtree(os.path.join(self.__dir, "sub"))

        # Reading drops the entry it was asked about, and only that one
        with self.assertRaises(CacheMiss):
            cache.get("key1")
        self.assertEqual(cache.size, 20)

        # Writing works again, even though the cache still thinks it's full
        cache.set("key4", val)
        self.assertEqual(cache.size, 30)

        self.assertFalse(cache.has("key2"))
        self.assertFalse(cache.has("key3"))
        self.assertTrue(cache.has("key4"))
        self.assertEqual(cache.size, 10)
        self.assertEqual(cache.get_value("key4"), val)

    def test_set_makedirs_error_propagates(self):
        # Same as at init: an error other than "already exists" must not be
        # swallowed by the write path
        cache = Cache(self.__dir, 10)
        with patch("os.makedirs", side_effect=OSError(errno.EACCES, "denied")):
            with self.assertRaises(OSError):
                cache.set("key", b"0123456789")

    @unittest.skipIf(
        os.name == "nt", "a directory holding an open file can't be removed on Windows"
    )
    def test_cache_dir_deleted_mid_write(self):
        # A long transcode can outlive a cleanup sweep. Writing keeps working
        # (POSIX keeps the inode alive for the open fd), yet the final
        # os.replace() fails as the temp file no longer has a path.
        cache_dir = os.path.join(self.__dir, "sub", "cache")
        cache = Cache(cache_dir, 30, min_time=0)
        val = b"0123456789"

        with cache.set_fileobj("key") as fp:
            fp.write(val)
            shutil.rmtree(os.path.join(self.__dir, "sub"))
            fp.write(val)

        self.assertTrue(os.path.isdir(cache_dir))
        self.assertEqual(cache.size, 20)
        self.assertEqual(cache.get_value("key"), val * 2)


if __name__ == "__main__":
    unittest.main()
