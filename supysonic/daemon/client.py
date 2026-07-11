# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from multiprocessing.connection import Client

from ..config import get_current_config
from ..utils import get_secret_key
from .commands import (
    AddWatchedFolderCommand,
    JukeboxCommand,
    RemoveWatchedFolder,
    ScannerProgressCommand,
    ScannerStartCommand,
)
from .exceptions import DaemonUnavailableError

__all__ = ["DaemonClient"]


class DaemonClient:
    def __init__(self, address=None):
        self.__address = address or get_current_config().DAEMON["socket"]
        self.__key = get_secret_key("daemon_key")

    def __get_connection(self):
        if not self.__address:
            raise DaemonUnavailableError("No daemon address set")
        try:
            return Client(address=self.__address, authkey=self.__key)
        except OSError:
            raise DaemonUnavailableError(
                f"Couldn't connect to daemon at {self.__address}"
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

    def scan(self, folders=None, force=False):
        if folders is None:
            folders = []
        if not isinstance(folders, (list, tuple)):
            raise TypeError("Expecting list, got " + str(type(folders)))
        with self.__get_connection() as c:
            c.send(ScannerStartCommand(folders, force))

    def jukebox_control(self, action, *args):
        if not isinstance(action, str):
            raise TypeError("Expecting string, got " + str(type(action)))
        with self.__get_connection() as c:
            c.send(JukeboxCommand(action, args))
            return c.recv()
