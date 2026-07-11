# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from ..db import close_connection, open_connection

__all__ = [
    "DaemonCommand",
    "WatcherCommand",
    "AddWatchedFolderCommand",
    "RemoveWatchedFolder",
    "ScannerCommand",
    "ScannerProgressCommand",
    "ScannerStartCommand",
    "JukeboxCommand",
    "DaemonCommandResult",
    "ScannerProgressResult",
    "JukeboxResult",
]


class DaemonCommand:
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
    def __init__(self, folders=None, force=False):
        self.__folders = folders or []
        self.__force = force

    def apply(self, connection, daemon):
        daemon.start_scan(self.__folders, self.__force)


class JukeboxCommand(DaemonCommand):
    def __init__(self, action, args):
        self.__action = action
        self.__args = args

    def apply(self, connection, daemon):
        if daemon.jukebox is None:
            connection.send(JukeboxResult(None))
            return

        playlist = None
        if self.__action == "get":
            playlist = daemon.jukebox.playlist
        elif self.__action == "status":
            pass
        else:
            func = None

            if self.__action == "set":
                func = daemon.jukebox.set
            elif self.__action == "start":
                func = daemon.jukebox.start
            elif self.__action == "stop":
                func = daemon.jukebox.stop
            elif self.__action == "skip":
                func = daemon.jukebox.skip
            elif self.__action == "add":
                func = daemon.jukebox.add
            elif self.__action == "clear":
                func = daemon.jukebox.clear
            elif self.__action == "remove":
                func = daemon.jukebox.remove
            elif self.__action == "shuffle":
                func = daemon.jukebox.shuffle
            elif self.__action == "setGain":
                func = daemon.jukebox.setgain

            # 'set' and 'add' resolve tracks from the database; make sure the
            # connection is opened and released in the daemon's handler thread
            # so it doesn't leak for the lifetime of the daemon.
            opened = open_connection(reuse=True)
            try:
                func(*self.__args)
            finally:
                if opened:
                    close_connection()

        rv = JukeboxResult(daemon.jukebox)
        rv.playlist = playlist
        connection.send(rv)


class DaemonCommandResult:
    pass


class ScannerProgressResult(DaemonCommandResult):
    def __init__(self, scanned):
        self.__scanned = scanned

    scanned = property(lambda self: self.__scanned)


class JukeboxResult(DaemonCommandResult):
    def __init__(self, jukebox):
        if jukebox is None:
            self.playing = False
            self.index = -1
            self.gain = 1.0
            self.position = 0
        else:
            self.playing = jukebox.playing
            self.index = jukebox.index
            self.gain = jukebox.gain
            self.position = jukebox.position
        self.playlist = ()
