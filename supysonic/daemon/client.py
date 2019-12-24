# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from multiprocessing.connection import Client

from .exceptions import DaemonUnavailableError
from ..config import get_current_config
from ..utils import get_secret_key

__all__ = ["DaemonClient"]


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
    def __init__(self, folders=[], force=False):
        self.__folders = folders
        self.__force = force

    def apply(self, connection, daemon):
        daemon.start_scan(self.__folders, self.__force)


class DaemonCommandResult(object):
    pass


class ScannerProgressResult(DaemonCommandResult):
    def __init__(self, scanned):
        self.__scanned = scanned

    scanned = property(lambda self: self.__scanned)


class DaemonClient(object):
    def __init__(self, address=None):
        self.__address = address or get_current_config().DAEMON["socket"]
        self.__key = get_secret_key("daemon_key")

    def __get_connection(self):
        if not self.__address:
            raise DaemonUnavailableError("No daemon address set")
        try:
            return Client(address=self.__address, authkey=self.__key)
        except IOError:
            raise DaemonUnavailableError(
                "Couldn't connect to daemon at {}".format(self.__address)
            )

    def add_watched_folder(self, folder):
        if not isinstance(folder, str):
            raise TypeError("Expecting string, got " + str(type(folder)))
        with self.__get_connection() as c:
            c.send(AddWatchedFolderCommand(folder))

    def remove_watched_folder(self, folder):
        if not isinstance(folder, str):
            raise TypeError("Expecting string, got " + str(type(folder)))
        with self.__get_connection() as c:
            c.send(RemoveWatchedFolder(folder))

    def get_scanning_progress(self):
        with self.__get_connection() as c:
            c.send(ScannerProgressCommand())
            return c.recv().scanned

    def scan(self, folders=[], force=False):
        if not isinstance(folders, list):
            raise TypeError("Expecting list, got " + str(type(folders)))
        with self.__get_connection() as c:
            c.send(ScannerStartCommand(folders, force))
