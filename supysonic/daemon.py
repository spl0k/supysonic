# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from multiprocessing.connection import Client, Listener
from pony.orm import db_session
from threading import Thread

from .db import Folder
from .config import get_current_config
from .py23 import strtype
from .scanner import Scanner
from .utils import get_secret_key
from .watcher import SupysonicWatcher

__all__ = [ 'Daemon', 'DaemonClient', 'DaemonUnavailableError' ]

logger = logging.getLogger(__name__)

class DaemonUnavailableError(Exception):
    pass

class ScannerAlreadyRunningError(Exception):
    pass

class DaemonCommand(object):
    def apply(self, connection, daemon):
        raise NotImplementedError()

class WatcherCommand(DaemonCommand):
    def __init__(self, folder):
        self._folder = folder

class AddWatchedFolderCommand(WatcherCommand):
    def apply(self, connection, daemon):
        if daemon.watcher is not None:
            daemon.watcher.add_folder(self._folder)

class RemoveWatchedFolder(WatcherCommand):
    def apply(self, connection, daemon):
        if daemon.watcher is not None:
            daemon.watcher.remove_folder(self._folder)

class ScannerCommand(DaemonCommand):
    pass

class ScannerProgressCommand(ScannerCommand):
    def apply(self, connection, daemon):
        scanner = daemon.scanner
        rv = scanner.scanned if scanner is not None and scanner.is_alive() else None
        connection.send(ScannerProgressResult(rv))

class ScannerStartCommand(ScannerCommand):
    def __init__(self, folders = [], force = False):
        self.__folders = folders
        self.__force = force

    def apply(self, connection, daemon):
        try:
            daemon.start_scan(self.__folders, self.__force)
            connection.send(ScannerStartResult(None))
        except ScannerAlreadyRunningError as e:
            connection.send(ScannerStartResult(e))

class DaemonCommandResult(object):
    pass

class ScannerProgressResult(DaemonCommandResult):
    def __init__(self, scanned):
        self.__scanned = scanned

    scanned = property(lambda self: self.__scanned)

class ScannerStartResult(DaemonCommandResult):
    def __init__(self, exception):
        self.__exception = exception

    exception = property(lambda self: self.__exception)

class DaemonClient(object):
    def __init__(self, address = None):
        self.__address = address or get_current_config().DAEMON['socket']
        self.__key = get_secret_key('daemon_key')

    def __get_connection(self):
        if not self.__address:
            raise DaemonUnavailableError('No daemon address set')
        try:
            return Client(address = self.__address, authkey = self.__key)
        except IOError:
            raise DaemonUnavailableError("Couldn't connect to daemon at {}".format(self.__address))

    def add_watched_folder(self, folder):
        if not isinstance(folder, strtype):
            raise TypeError('Expecting string, got ' + str(type(folder)))
        with self.__get_connection() as c:
            c.send(AddWatchedFolderCommand(folder))

    def remove_watched_folder(self, folder):
        if not isinstance(folder, strtype):
            raise TypeError('Expecting string, got ' + str(type(folder)))
        with self.__get_connection() as c:
            c.send(RemoveWatchedFolder(folder))

    def get_scanning_progress(self):
        with self.__get_connection() as c:
            c.send(ScannerProgressCommand())
            return c.recv().scanned

    def scan(self, folders = [], force = False):
        if not isinstance(folders, list):
            raise TypeError('Expecting list, got ' + str(type(folders)))
        with self.__get_connection() as c:
            c.send(ScannerStartCommand(folders, force))
            rv = c.recv()
            if rv.exception is not None:
                raise rv.exception

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
        if self.__scanner is not None and self.__scanner.is_alive():
            raise ScannerAlreadyRunningError()

        extensions = self.__config.BASE['scanner_extensions']
        if extensions:
            extensions = extensions.split(' ')

        self.__scanner = ScannerThread(args = folders, kwargs = { 'force': force, 'extensions': extensions })
        self.__scanner.start()

    def terminate(self):
        self.__listener.close()
        if self.__watcher is not None:
            self.__watcher.stop()

class ScannerThread(Thread):
    def __init__(self, *args, **kwargs):
        super(ScannerThread, self).__init__(*args, **kwargs)
        self.__scanned = {}

    def run(self):
        force = self._kwargs.get('force', False)
        extensions = self._kwargs.get('extensions')
        s = Scanner(force = force, extensions = extensions)

        with db_session:
            if self._args:
                folders = Folder.select(lambda f: f.root and f.name in self._args)
            else:
                folders = Folder.select(lambda f: f.root)

            for f in folders:
                name = f.name
                logger.info('Scanning %s', name)
                s.scan(f, lambda x: self.__scanned.update({ name: x }))

            s.finish()

    @property
    def scanned(self):
        # This isn't quite thread-safe but locking each time a file is scanned could affect performance
        return sum(self.__scanned.values())
