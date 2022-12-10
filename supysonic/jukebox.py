# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import shlex
import time

from datetime import datetime, timedelta
from random import shuffle
from subprocess import Popen, DEVNULL
from threading import Thread, Event, RLock

from .db import Track

logger = logging.getLogger(__name__)


class Jukebox:
    def __init__(self, cmd):
        self.__cmd = shlex.split(cmd)
        self.__playlist = []
        self.__index = 0
        self.__offset = 0
        self.__start = None

        self.__thread = None
        self.__lock = RLock()
        self.__skip = Event()
        self.__stop = Event()

    playing = property(
        lambda self: self.__thread is not None and self.__thread.is_alive()
    )
    index = property(lambda self: self.__index)
    gain = property(lambda self: 1.0)
    playlist = property(lambda self: list(self.__playlist))

    @property
    def position(self):
        if self.__start is None:
            return 0
        return int((datetime.utcnow() - self.__start).total_seconds())

    def set(self, *tracks):
        self.clear()
        self.add(*tracks)

    def start(self):
        if self.playing or not self.__playlist:
            return

        self.__skip.clear()
        self.__stop.clear()
        self.__offset = 0
        self.__thread = Thread(target=self.__play_thread)
        self.__thread.start()

    def stop(self):
        if not self.playing:
            return

        self.__stop.set()

    def skip(self, index, offset):
        if index < 0 or index >= len(self.__playlist):
            raise IndexError()
        if offset < 0:
            raise ValueError()

        with self.__lock:
            self.__index = index
            self.__offset = offset
            self.__start = datetime.utcnow() - timedelta(seconds=offset)
        self.__skip.set()
        self.start()

    def add(self, *tracks):
        with self.__lock:
            for t in tracks:
                try:
                    self.__playlist.append(Track[t].path)
                except Track.DoesNotExist:
                    pass

    def clear(self):
        with self.__lock:
            self.__playlist.clear()
            self.__index = 0
            self.__offset = 0

    def remove(self, index):
        try:
            with self.__lock:
                self.__playlist.pop(index)
                if index < self.__index:
                    self.__index -= 1
        except IndexError:
            pass

    def shuffle(self):
        with self.__lock:
            shuffle(self.__playlist)

    def setgain(self, gain):
        pass

    def terminate(self):
        self.__stop.set()
        if self.__thread is not None:
            self.__thread.join()

    def __play_thread(self):
        proc = None
        while not self.__stop.is_set():
            if self.__skip.is_set():
                proc.terminate()
                proc.wait()
                proc = None
                self.__skip.clear()

            if proc is None:
                with self.__lock:
                    proc = self.__play_file()
            elif proc.poll() is not None:
                with self.__lock:
                    self.__start = None
                    self.__index += 1
                    if self.__index >= len(self.__playlist):
                        break

                    proc = self.__play_file()

            time.sleep(0.1)

        proc.terminate()
        proc.wait()
        self.__start = None

    def __play_file(self):
        path = self.__playlist[self.__index]
        args = [
            a.replace("%path", path).replace("%offset", str(self.__offset))
            for a in self.__cmd
        ]

        self.__start = datetime.utcnow() - timedelta(seconds=self.__offset)
        self.__offset = 0

        logger.debug("Start playing with command %s", args)
        try:
            return Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        except Exception:
            logger.exception("Failed to run play command")
            return None
