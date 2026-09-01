# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from multiprocessing.connection import Client

from ..db import get_secret_key
from ..parsers import ensure_list, ensure_str
from .commands import (
    AddWatchedFolderCommand,
    JukeboxCommand,
    RemoveWatchedFolder,
    ScannerProgressCommand,
    ScannerStartCommand,
    decode,
    encode,
)
from .exceptions import DaemonUnavailableError

__all__ = ["DaemonClient"]


class DaemonClient:
    def __init__(self, address):
        self.__address = address
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

    def _send(self, cmd, expect_result=False):
        with self.__get_connection() as c:
            c.send_bytes(encode(cmd))
            if expect_result:
                return decode(c.recv_bytes())

    def add_watched_folder(self, folder):
        ensure_str(folder)
        self._send(AddWatchedFolderCommand(folder))

    def remove_watched_folder(self, folder):
        ensure_str(folder)
        self._send(RemoveWatchedFolder(folder))

    def get_scanning_progress(self):
        return self._send(ScannerProgressCommand(), True).scanned

    def scan(self, folders=None, force=False):
        if folders is None:
            folders = []
        ensure_list(folders)
        self._send(ScannerStartCommand(folders, force))

    def jukebox_control(self, action, *args):
        ensure_str(action)
        return self._send(JukeboxCommand(action, args), True)
