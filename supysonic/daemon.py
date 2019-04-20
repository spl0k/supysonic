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

from .config import get_current_config
from .py23 import strtype
from .utils import get_secret_key
from .watcher import SupysonicWatcher

__all__ = [ 'Daemon', 'DaemonClient', 'DaemonUnavailableError' ]

logger = logging.getLogger(__name__)

class DaemonUnavailableError(Exception):
    pass

class DaemonCommand(object):
    def apply(self, connection, *args):
        raise NotImplementedError()

class WatcherCommand(DaemonCommand):
    def __init__(self, folder):
        self._folder = folder

class AddWatchedFolderCommand(WatcherCommand):
    def apply(self, connection, watcher):
        watcher.add_folder(self._folder)

class RemoveWatchedFolder(WatcherCommand):
    def apply(self, connection, watcher):
        watcher.remove_folder(self._folder)

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

class Daemon(object):
    def __init__(self, address):
        self.__address = address
        self.__listener = None
        self.__watcher = None

    def __handle_connection(self, connection):
        cmd = connection.recv()
        logger.debug('Received %s', cmd)
        if self.__watcher is not None and isinstance(cmd, WatcherCommand):
            cmd.apply(connection, self.__watcher)

    def run(self, config):
        self.__listener = Listener(address = self.__address, authkey = get_secret_key('daemon_key'))
        logger.info("Listening to %s", self.__listener.address)

        if config.DAEMON['run_watcher']:
            self.__watcher = SupysonicWatcher(config)
            self.__watcher.start()

        while True:
            conn = self.__listener.accept()
            self.__handle_connection(conn)

    def terminate(self):
        self.__listener.close()
        if self.__watcher is not None:
            self.__watcher.stop()
