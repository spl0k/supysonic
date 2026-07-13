# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from functools import singledispatchmethod
from json import JSONDecodeError
from multiprocessing.connection import Client, Listener
from threading import Event, Thread

from ..db import Folder, close_connection, open_connection
from ..jukebox import Jukebox
from ..scanner import Scanner
from ..utils import get_secret_key
from ..watcher import SupysonicWatcher
from .commands import (
    AddWatchedFolderCommand,
    JukeboxCommand,
    JukeboxResult,
    RemoveWatchedFolder,
    ScannerProgressCommand,
    ScannerProgressResult,
    ScannerStartCommand,
    StopCommand,
    decode,
    encode,
)
from .exceptions import UnknownCommandError

__all__ = ["Daemon"]

logger = logging.getLogger(__name__)


class Daemon:
    def __init__(self, config):
        self.__config = config
        self.__listener = None
        self.__watcher = None
        self.__scanner = None
        self.__jukebox = None
        self.__stopped = Event()

    watcher = property(lambda self: self.__watcher)
    scanner = property(lambda self: self.__scanner)
    jukebox = property(lambda self: self.__jukebox)

    def __handle_connection(self, connection):
        try:
            cmd = decode(connection.recv_bytes())
        except UnknownCommandError as e:
            logger.warning("Received unknown command %r", e.tag)
            return
        except JSONDecodeError:
            logger.warning("Received malformed payload")
            return

        logger.debug("Received %s", cmd)
        self.__handle(cmd, connection)

    @singledispatchmethod
    def __handle(self, cmd, connection):
        raise UnknownCommandError(cmd.type)

    @__handle.register
    def _(self, cmd: StopCommand, connection):
        self.__stopped.set()

    @__handle.register
    def _(self, cmd: AddWatchedFolderCommand, connection):
        if self.__watcher is not None:
            self.__watcher.add_folder(cmd.folder)

    @__handle.register
    def _(self, cmd: RemoveWatchedFolder, connection):
        if self.__watcher is not None:
            self.__watcher.remove_folder(cmd.folder)

    @__handle.register
    def _(self, cmd: ScannerProgressCommand, connection):
        scanner = self.__scanner
        rv = scanner.scanned if scanner is not None and scanner.is_alive() else None
        connection.send_bytes(encode(ScannerProgressResult(rv)))

    @__handle.register
    def _(self, cmd: ScannerStartCommand, connection):
        self.start_scan(cmd.folders, cmd.force)

    @__handle.register
    def _(self, cmd: JukeboxCommand, connection):
        if self.__jukebox is None:
            connection.send_bytes(encode(JukeboxResult.from_jukebox(None)))
            return

        playlist = None
        if cmd.action == "get":
            playlist = self.__jukebox.playlist
        elif cmd.action == "status":
            pass
        else:
            func = None

            if cmd.action == "set":
                func = self.__jukebox.set
            elif cmd.action == "start":
                func = self.__jukebox.start
            elif cmd.action == "stop":
                func = self.__jukebox.stop
            elif cmd.action == "skip":
                func = self.__jukebox.skip
            elif cmd.action == "add":
                func = self.__jukebox.add
            elif cmd.action == "clear":
                func = self.__jukebox.clear
            elif cmd.action == "remove":
                func = self.__jukebox.remove
            elif cmd.action == "shuffle":
                func = self.__jukebox.shuffle
            elif cmd.action == "setGain":
                func = self.__jukebox.setgain

            # 'set' and 'add' resolve tracks from the database; make sure the
            # connection is opened and released in the daemon's handler thread
            # so it doesn't leak for the lifetime of the daemon.
            opened = open_connection(reuse=True)
            try:
                func(*cmd.args)
            finally:
                if opened:
                    close_connection()

        connection.send_bytes(
            encode(JukeboxResult.from_jukebox(self.__jukebox, playlist))
        )

    def run(self):
        self.__listener = Listener(
            address=self.__config.DAEMON["socket"], authkey=get_secret_key("daemon_key")
        )
        logger.info("Listening to %s", self.__listener.address)

        if self.__config.DAEMON["run_watcher"]:
            self.__watcher = SupysonicWatcher(self.__config)
            self.__watcher.start()

        if self.__config.DAEMON["jukebox_command"]:
            self.__jukebox = Jukebox(self.__config.DAEMON["jukebox_command"])

        close_connection()

        Thread(target=self.__listen).start()
        while not self.__stopped.wait(1):
            pass

        # A StopCommand woke us up: tear the subsystems down here, symmetrically
        # with the setup above
        if self.__scanner is not None:
            self.__scanner.stop()
            self.__scanner.join()
        if self.__watcher is not None:
            self.__watcher.stop()
        if self.__jukebox is not None:
            self.__jukebox.terminate()

    def __listen(self):
        while not self.__stopped.is_set():
            try:
                with self.__listener.accept() as conn:
                    self.__handle_connection(conn)
            except Exception as exc:
                logger.exception(exc)

        self.__listener.close()

    def start_scan(self, folders=None, force=False):
        if not folders:
            open_connection()
            folders = [
                t[0] for t in Folder.select(Folder.name).where(Folder.root).tuples()
            ]
            close_connection()

        if self.__scanner is not None and self.__scanner.is_alive():
            for f in folders:
                self.__scanner.queue_folder(f)
            return

        extensions = self.__config.BASE["scanner_extensions"]
        if extensions:
            extensions = extensions.split(" ")

        self.__scanner = Scanner(
            force=force,
            extensions=extensions,
            follow_symlinks=self.__config.BASE["follow_symlinks"],
            on_folder_start=self.__unwatch,
            on_folder_end=self.__watch,
        )
        for f in folders:
            self.__scanner.queue_folder(f)

        self.__scanner.start()

    def __watch(self, folder):
        if self.__watcher is not None:
            self.__watcher.add_folder(folder.path)

    def __unwatch(self, folder):
        if self.__watcher is not None:
            self.__watcher.remove_folder(folder.path)

    def terminate(self):
        if self.__listener is None:
            logger.warning(
                "Trying to stop the daemon before it had the chance to start"
            )
            return

        with Client(self.__listener.address, authkey=get_secret_key("daemon_key")) as c:
            c.send_bytes(encode(StopCommand()))
