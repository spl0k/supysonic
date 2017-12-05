#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import os
import shutil
import tempfile
import time
import unittest

from contextlib import contextmanager
from threading import Thread

from supysonic.db import get_store, Track, Artist
from supysonic.managers.folder import FolderManager
from supysonic.watcher import SupysonicWatcher

from ..testbase import TestConfig

class WatcherTestConfig(TestConfig):
    DAEMON = {
        'wait_delay': 0.5,
        'log_file': None,
        'log_level': 'DEBUG'
    }

    def __init__(self, db_uri):
        super(WatcherTestConfig, self).__init__(False, False)
        self.BASE['database_uri'] = db_uri

class WatcherTestBase(unittest.TestCase):
    @contextmanager
    def _get_store(self):
        store = None
        try:
            store = get_store('sqlite:///' + self.__dbfile)
            yield store
            store.commit()
            store.close()
        except:
            store.rollback()
            store.close()
            raise

    def setUp(self):
        self.__dbfile = tempfile.mkstemp()[1]
        conf = WatcherTestConfig('sqlite:///' + self.__dbfile)
        self.__sleep_time = conf.DAEMON['wait_delay'] + 1

        with self._get_store() as store:
            with io.open('schema/sqlite.sql', 'r') as sql:
                schema = sql.read()
                for statement in schema.split(';'):
                    store.execute(statement)

        self.__watcher = SupysonicWatcher(conf)
        self.__thread = Thread(target = self.__watcher.run)

    def tearDown(self):
        os.unlink(self.__dbfile)

    def _start(self):
        self.__thread.start()
        time.sleep(0.2)

    def _stop(self):
        self.__watcher.stop()
        self.__thread.join()

    def _is_alive(self):
        return self.__thread.is_alive()

    def _sleep(self):
        time.sleep(self.__sleep_time)

class NothingToWatchTestCase(WatcherTestBase):
    def test_spawn_useless_watcher(self):
        self._start()
        time.sleep(0.2)
        self.assertFalse(self._is_alive())
        self._stop()

class WatcherTestCase(WatcherTestBase):
    def setUp(self):
        super(WatcherTestCase, self).setUp()
        self.__dir = tempfile.mkdtemp()
        with self._get_store() as store:
            FolderManager.add(store, 'Folder', self.__dir)
        self._start()

    def tearDown(self):
        self._stop()
        shutil.rmtree(self.__dir)
        super(WatcherTestCase, self).tearDown()

    @staticmethod
    def _tempname():
        with tempfile.NamedTemporaryFile() as f:
            return os.path.basename(f.name)

    def assertTrackCountEqual(self, expected):
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), expected)

    def test_add(self):
        shutil.copyfile('tests/assets/folder/silence.mp3', os.path.join(self.__dir, self._tempname() + '.mp3'))
        self.assertTrackCountEqual(0)
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_add_nowait_stop(self):
        shutil.copyfile('tests/assets/folder/silence.mp3', os.path.join(self.__dir, self._tempname() + '.mp3'))
        self._stop()
        self.assertTrackCountEqual(1)

    def test_add_multiple(self):
        shutil.copyfile('tests/assets/folder/silence.mp3', os.path.join(self.__dir, self._tempname() + '.mp3'))
        shutil.copyfile('tests/assets/folder/silence.mp3', os.path.join(self.__dir, self._tempname() + '.mp3'))
        shutil.copyfile('tests/assets/folder/silence.mp3', os.path.join(self.__dir, self._tempname() + '.mp3'))
        self.assertTrackCountEqual(0)
        self._sleep()
        with self._get_store() as store:
            self.assertEqual(store.find(Track).count(), 3)
            self.assertEqual(store.find(Artist).count(), 1)

def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(NothingToWatchTestCase))
    suite.addTest(unittest.makeSuite(WatcherTestCase))

    return suite

if __name__ == '__main__':
    unittest.main()

