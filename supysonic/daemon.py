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

from .config import IniConfig
from .py23 import strtype
from .utils import get_secret_key
from .watcher import SupysonicWatcher

__all__ = [ 'Daemon', 'DaemonClient' ]

logger = logging.getLogger(__name__)

WATCHER = 0

W_ADD = 0
W_DEL = 1

class DaemonClient(object):
    def __init__(self, address = None):
        self.__address = address or IniConfig.from_common_locations().DAEMON['socket']
        self.__key = get_secret_key('daemon_key')

    def __get_connection(self):
        return Client(address = self.__address, authkey = self.__key)

    def add_watched_folder(self, folder):
        if not isinstance(folder, strtype):
            raise TypeError('Expecting string, got ' + str(type(folder)))
        with self.__get_connection() as c:
            c.send((WATCHER, W_ADD, folder))

    def remove_watched_folder(self, folder):
        if not isinstance(folder, strtype):
            raise TypeError('Expecting string, got ' + str(type(folder)))
        with self.__get_connection() as c:
            c.send((WATCHER, W_DEL, folder))

class Daemon(object):
    def __init__(self, address):
        self.__address = address
        self.__listener = None
        self.__watcher = None

    def __handle_connection(self, connection):
        try:
            module, cmd, *args = connection.recv()
            if module == WATCHER:
                if cmd == W_ADD:
                    self.__watcher.add_folder(*args)
                elif cmd == W_DEL:
                    self.__watcher.remove_folder(*args)
        except ValueError:
            logger.warn('Received unknown data')

    def run(self, config):
        self.__listener = Listener(address = self.__address, authkey = get_secret_key('daemon_key'))
        logger.info("Listening to %s", self.__listener.address)

        self.__watcher = SupysonicWatcher(config)
        self.__watcher.start()

        while True:
            conn = self.__listener.accept()
            self.__handle_connection(conn)

    def terminate(self):
        self.__listener.close()
        self.__watcher.stop()
