# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2019 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

from collections import OrderedDict, namedtuple
import contextlib
import errno
import logging
import os
import os.path
import tempfile
import threading
from time import time


logger = logging.getLogger(__name__)


class CacheMiss(KeyError):
    """The requested data is not in the cache"""

    pass


class ProtectedError(Exception):
    """The data cannot be purged from the cache"""

    pass


CacheEntry = namedtuple("CacheEntry", ["size", "expires"])
NULL_ENTRY = CacheEntry(0, 0)


class Cache:
    """Provides a common interface for caching files to disk"""

    # Modeled after werkzeug.contrib.cache.FileSystemCache

    # keys must be filename-compatible strings (no paths)
    # values must be bytes (not strings)

    def __init__(self, cache_dir, max_size, min_time=300, auto_prune=True):
        """Initialize the cache

        cache_dir: The folder to store cached files
        max_size: The maximum allowed size of the cache in bytes
        min_time: The minimum amount of time a file will be stored in the cache
                  in seconds (default 300 = 5min)
        auto_prune: If True (default) the cache will automatically be pruned to
                    the max_size when possible.

        Note that max_size is not a hard restriction and in some cases will
        temporarily be exceeded, even when auto-pruning is turned on.
        """
        self._cache_dir = os.path.abspath(cache_dir)
        self.min_time = min_time
        self.max_size = max_size
        self._auto_prune = auto_prune
        self._lock = threading.RLock()

        # Create the cache directory
        try:
            os.makedirs(self._cache_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Make a key -> CacheEntry(size, expiry) map ordered by mtime
        self._size = 0
        self._files = OrderedDict()
        for mtime, size, key in sorted(
            [
                (f.stat().st_mtime, f.stat().st_size, f.name)
                for f in os.scandir(self._cache_dir)
                if f.is_file()
            ]
        ):
            self._files[key] = CacheEntry(size, mtime + self.min_time)
            self._size += size

    def _filepath(self, key):
        return os.path.join(self._cache_dir, key)

    def _make_space(self, required_space, key=None):
        """Delete files to free up the required space (or close to it)

        If key is provided and exists in the cache, its size will be
        subtracted from the required size.
        """
        target = self.max_size - required_space
        if key is not None:
            target += self._files.get(key, NULL_ENTRY).size

        with self._lock:
            # Delete the oldest file until self._size <= target
            for k in list(self._files.keys()):
                if self._size <= target:
                    break
                try:
                    self.delete(k)
                except ProtectedError:
                    pass

    def _record_file(self, key, size):
        # If the file is being replaced, add only the difference in size
        self._size += size - self._files.get(key, NULL_ENTRY).size
        self._files[key] = CacheEntry(size, int(time()) + self.min_time)

    def _freshen_file(self, key):
        """Touch the file to change modified time and move it to the end of the cache dict"""
        old = self._files.pop(key)
        self._files[key] = CacheEntry(old.size, int(time()) + self.min_time)
        os.utime(self._filepath(key), None)

    @property
    def size(self):
        """The current amount of data cached"""
        return self._size

    def touch(self, key):
        """Mark a cache entry as fresh"""
        with self._lock:
            if not self.has(key):
                raise CacheMiss(key)
            self._freshen_file(key)

    @contextlib.contextmanager
    def set_fileobj(self, key):
        """Yields a file object that can have bytes written to it in order to
        store them in the cache.

        The contents of the file object will be stored in the cache when the
        context is exited.

        Ex:
        >>> with cache.set_fileobj(key) as fp:
        ...     json.dump(some_data, fp)
        """
        f = tempfile.NamedTemporaryFile(
            dir=self._cache_dir, suffix=".part", delete=False
        )
        try:
            yield f

            # seek to end and get position to get filesize
            f.seek(0, 2)
            size = f.tell()
            f.close()

            with self._lock:
                if self._auto_prune:
                    self._make_space(size, key=key)
                os.replace(f.name, self._filepath(key))
                self._record_file(key, size)
        except BaseException:
            f.close()
            with contextlib.suppress(OSError):
                os.remove(f.name)
            raise

    def set(self, key, value):
        """Set a literal value into the cache and return its path"""
        with self.set_fileobj(key) as f:
            f.write(value)
        return self._filepath(key)

    def set_generated(self, key, gen_function):
        """Pass the values yielded from the generator function through and set
        the end result in the cache.

        The contents will be set into the cache only if and when the generator
        completes.

        Ex:
        >>> for x in cache.set_generated(key, generator_function):
        ...     print(x)
        """
        with self.set_fileobj(key) as f:
            gen = gen_function()
            try:
                for data in gen:
                    f.write(data)
                    yield data
            except GeneratorExit:
                # Try to stop the generator but check it still wants to yield data.
                # If it does allow caching of this data without forwarding it
                try:
                    f.write(gen.throw(GeneratorExit))
                    for data in gen:
                        f.write(data)
                except StopIteration:
                    # We stopped just at the end of the generator
                    pass

    def get(self, key):
        """Return the path to the file where the cached data is stored"""
        self.touch(key)
        return self._filepath(key)

    @contextlib.contextmanager
    def get_fileobj(self, key):
        """Yields a file object that can be used to read cached bytes"""
        with open(self.get(key), "rb") as f:
            yield f

    def get_value(self, key):
        """Return the cached data"""
        with self.get_fileobj(key) as f:
            return f.read()

    def delete(self, key):
        """Delete a file from the cache"""
        with self._lock:
            if not self.has(key):
                return
            if time() < self._files[key].expires:
                raise ProtectedError("File has not expired")

            os.remove(self._filepath(key))
            self._size -= self._files.pop(key).size

    def prune(self):
        """Prune the cache down to the max size

        Note that protected files are not deleted
        """
        self._make_space(0)

    def clear(self):
        """Clear the cache

        Note that protected files are not deleted
        """
        self._make_space(self.max_size)

    def has(self, key):
        """Check if a key is currently cached"""
        if key not in self._files:
            return False

        if not os.path.exists(self._filepath(key)):
            # Underlying file is gone, remove from the cache
            self._size -= self._files.pop(key).size
            return False

        return True
