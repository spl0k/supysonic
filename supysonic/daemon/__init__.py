# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

from multiprocessing.connection import Listener
from pony.orm import db_session, select
from threading import Thread

from .client import DaemonCommand
from ..db import Folder
from ..scanner import Scanner
from ..utils import get_secret_key
from ..watcher import SupysonicWatcher

__all__ = [ 'Daemon' ]

logger = logging.getLogger(__name__)

class Daemon(object):
    def __init__(self, config):
        self.__config = config
        self.__listener = None
        self.__watcher = None
        self.__scanner = None

    watcher = property(lambda self: self.__watcher)
    scanner = property(lambda self: self.__scanner)

    def __handle_connection(self, connection):
        cmd = connection.recv()
        logger.debug('Received %s', cmd)
        if isinstance(cmd, DaemonCommand):
            cmd.apply(connection, self)
        else:
            logger.warn('Received unknown command %s', cmd)

    def run(self):
        self.__listener = Listener(address = self.__config.DAEMON['socket'], authkey = get_secret_key('daemon_key'))
        logger.info("Listening to %s", self.__listener.address)

        if self.__config.DAEMON['run_watcher']:
            self.__watcher = SupysonicWatcher(self.__config)
            self.__watcher.start()

        while True:
            conn = self.__listener.accept()
            self.__handle_connection(conn)

    def start_scan(self, folders = [], force = False):
        if not folders:
            with db_session:
                folders = select(f.name for f in Folder if f.root)[:]

        if self.__scanner is not None and self.__scanner.is_alive():
            for f in folders:
                self.__scanner.queue_folder(f)
            return

        extensions = self.__config.BASE['scanner_extensions']
        if extensions:
            extensions = extensions.split(' ')

        self.__scanner = ScannerThread(self.__watcher, kwargs = { 'force': force, 'extensions': extensions, 'notify_watcher': False })
        for f in folders:
            self.__scanner.queue_folder(f)

        self.__scanner.start()

    def terminate(self):
        self.__listener.close()
        if self.__watcher is not None:
            self.__watcher.stop()

class ScanQueue(Queue):
    def _init(self, maxsize):
        self.queue = set()
        self.__last_got = None

    def _put(self, item):
        if self.__last_got != item:
            self.queue.add(item)

    def _get(self):
        self.__last_got = self.queue.pop()
        return self.__last_got

class ScannerThread(Thread):
    def __init__(self, watcher, *args, **kwargs):
        super(ScannerThread, self).__init__(*args, **kwargs)
        self.__watcher = watcher
        self.__scanned = {}
        self.__queue = ScanQueue()

    def queue_folder(self, folder):
        self.__queue.put(folder)

    def run(self):
        s = Scanner(*self._args, **self._kwargs)

        with db_session:
            try:
                while True:
                    name = self.__queue.get(False)
                    folder = Folder.get(root = True, name = name)
                    if folder is None:
                        continue

                    if self.__watcher is not None:
                        self.__watcher.remove_folder(folder)
                    try:
                        logger.info('Scanning %s', name)
                        s.scan(folder, lambda x: self.__scanned.update({ name: x }))
                    finally:
                        if self.__watcher is not None:
                            self.__watcher.add_folder(folder)
            except Empty:
                pass

            s.finish()

    @property
    def scanned(self):
        # This isn't quite thread-safe but locking each time a file is scanned could affect performance
        return sum(self.__scanned.values())
