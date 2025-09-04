# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2014-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os.path
import time

from threading import Thread, Condition, Timer
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from . import covers
from .db import Folder, open_connection, close_connection
from .scanner import Scanner

OP_SCAN = 1
OP_REMOVE = 2
OP_MOVE = 4
FLAG_CREATE = 8
FLAG_COVER = 16

logger = logging.getLogger(__name__)


class SupysonicWatcherEventHandler(PatternMatchingEventHandler):
    def __init__(self, extensions):
        patterns = None
        if extensions:
            patterns = ["*." + e.lower() for e in extensions.split()] + [
                "*" + e for e in covers.EXTENSIONS
            ]
        super().__init__(patterns=patterns, ignore_directories=True)

    def dispatch(self, event):
        try:
            super().dispatch(event)
        except Exception as e:  # pragma: nocover
            logger.critical(e)

    def on_created(self, event):
        logger.debug("File created: '%s'", event.src_path)

        op = OP_SCAN | FLAG_CREATE
        if covers.is_valid_cover(event.src_path):
            op |= FLAG_COVER
        self.queue.put(event.src_path, op)

    def on_deleted(self, event):
        logger.debug("File deleted: '%s'", event.src_path)

        op = OP_REMOVE
        _, ext = os.path.splitext(event.src_path)
        if ext in covers.EXTENSIONS:
            op |= FLAG_COVER
        self.queue.put(event.src_path, op)

    def on_modified(self, event):
        logger.debug("File modified: '%s'", event.src_path)
        op = OP_SCAN
        if covers.is_valid_cover(event.src_path):
            op |= FLAG_COVER
        self.queue.put(event.src_path, op)

    def on_moved(self, event):
        logger.debug("File moved: '%s' -> '%s'", event.src_path, event.dest_path)

        op = OP_MOVE
        _, ext = os.path.splitext(event.src_path)
        if ext in covers.EXTENSIONS:
            op |= FLAG_COVER
        self.queue.put(event.dest_path, op, src_path=event.src_path)


class Event:
    def __init__(self, path, operation, **kwargs):
        if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
            raise Exception("Flags SCAN and REMOVE both set")  # pragma: nocover

        self.__path = path
        self.__time = time.time()
        self.__op = operation
        self.__src = kwargs.get("src_path")

    def set(self, operation, **kwargs):
        if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
            raise Exception("Flags SCAN and REMOVE both set")  # pragma: nocover

        self.__time = time.time()
        if operation & OP_SCAN:
            self.__op &= ~OP_REMOVE
        if operation & OP_REMOVE:
            self.__op &= ~OP_SCAN
        if operation & FLAG_CREATE:
            self.__op &= ~OP_MOVE
        self.__op |= operation

        src_path = kwargs.get("src_path")
        if src_path:
            self.__src = src_path

    @property
    def path(self):
        return self.__path

    @property
    def time(self):
        return self.__time

    @property
    def operation(self):
        return self.__op

    @property
    def src_path(self):
        return self.__src


class ScannerProcessingQueue(Thread):
    def __init__(self, delay):
        super().__init__()

        self.__timeout = delay
        self.__cond = Condition()
        self.__timer = None
        self.__queue = {}
        self.__running = True

    def run(self):
        try:
            self.__run()
        except Exception as e:  # pragma: nocover
            logger.critical(e)
            raise e

    def __run(self):
        while self.__running:
            time.sleep(0.1)

            with self.__cond:
                # Flag might have flipped during sleep. Check it again before waiting
                # See issue #263
                if self.__running:
                    self.__cond.wait()

                if not self.__queue:
                    continue

            logger.debug("Instantiating scanner")
            open_connection()
            scanner = Scanner()

            item = self.__next_item()
            while item:
                if item.operation & FLAG_COVER:
                    self.__process_cover_item(scanner, item)
                else:
                    self.__process_regular_item(scanner, item)

                item = self.__next_item()

            scanner.prune()
            close_connection()
            logger.debug("Freeing scanner")

    def __process_regular_item(self, scanner, item):
        if item.operation & OP_MOVE:
            logger.info("Moving: '%s' -> '%s'", item.src_path, item.path)
            scanner.move_file(item.src_path, item.path)

        if item.operation & OP_SCAN:
            logger.info("Scanning: '%s'", item.path)
            scanner.scan_file(item.path)

        if item.operation & OP_REMOVE:
            logger.info("Removing: '%s'", item.path)
            scanner.remove_file(item.path)

    def __process_cover_item(self, scanner, item):
        if item.operation & OP_SCAN:
            if os.path.isdir(item.path):
                logger.info("Looking for covers: '%s'", item.path)
                scanner.find_cover(item.path)
            else:
                logger.info("Potentially adding cover: '%s'", item.path)
                scanner.add_cover(item.path)

        if item.operation & OP_REMOVE:
            logger.info("Removing cover: '%s'", item.path)
            scanner.find_cover(os.path.dirname(item.path))

        if item.operation & OP_MOVE:
            logger.info("Moving cover: '%s' -> '%s'", item.src_path, item.path)
            scanner.find_cover(os.path.dirname(item.src_path))
            scanner.add_cover(item.path)

    def stop(self):
        with self.__cond:
            self.__running = False
            self.__cond.notify()

    def put(self, path, operation, **kwargs):
        if not self.__running:
            raise RuntimeError("Trying to put an item in a stopped queue")

        with self.__cond:
            if path in self.__queue:
                event = self.__queue[path]
                event.set(operation, **kwargs)
            else:
                event = Event(path, operation, **kwargs)
                self.__queue[path] = event

            if operation & OP_MOVE and kwargs["src_path"] in self.__queue:
                previous = self.__queue[kwargs["src_path"]]
                event.set(previous.operation, src_path=previous.src_path)
                del self.__queue[kwargs["src_path"]]

            if self.__timer:
                self.__timer.cancel()
            self.__timer = Timer(self.__timeout, self.__wakeup)
            self.__timer.start()

    def unschedule_paths(self, basepath):
        with self.__cond:
            for path in list(self.__queue):
                if path.startswith(basepath):
                    del self.__queue[path]

    def __wakeup(self):
        with self.__cond:
            self.__cond.notify()
            self.__timer = None

    def __next_item(self):
        with self.__cond:
            if not self.__queue:
                return None

            next = min(self.__queue.items(), key=lambda i: i[1].time)
            if not self.__running or next[1].time + self.__timeout <= time.time():
                del self.__queue[next[0]]
                return next[1]

            return None


class SupysonicWatcher:
    def __init__(self, config):
        self.__delay = config.DAEMON["wait_delay"]
        self.__handler = SupysonicWatcherEventHandler(config.BASE["scanner_extensions"])

        self.__folders = {}
        self.__queue = None
        self.__observer = None

    def add_folder(self, folder):
        if isinstance(folder, Folder):
            path = folder.path
        elif isinstance(folder, str):
            path = folder
        else:
            raise TypeError("Expecting string or Folder, got " + str(type(folder)))

        logger.info("Scheduling watcher for %s", path)
        watch = self.__observer.schedule(self.__handler, path, recursive=True)
        self.__folders[path] = watch

    def remove_folder(self, folder):
        if isinstance(folder, Folder):
            path = folder.path
        elif isinstance(folder, str):
            path = folder
        else:
            raise TypeError("Expecting string or Folder, got " + str(type(folder)))

        logger.info("Unscheduling watcher for %s", path)
        self.__observer.unschedule(self.__folders[path])
        del self.__folders[path]
        self.__queue.unschedule_paths(path)

    def start(self):
        self.__queue = ScannerProcessingQueue(self.__delay)
        self.__observer = Observer()
        self.__handler.queue = self.__queue

        for folder in Folder.select().where(Folder.root):
            self.add_folder(folder)

        logger.info("Starting watcher")
        self.__queue.start()
        self.__observer.start()

    def stop(self):
        logger.info("Stopping watcher")
        if self.__observer is not None:
            self.__observer.stop()
            self.__observer.join()
        if self.__queue is not None:
            self.__queue.stop()
            self.__queue.join()

        self.__observer = None
        self.__queue = None
        self.__handler.queue = None

    @property
    def running(self):
        return (
            self.__queue is not None
            and self.__observer is not None
            and self.__queue.is_alive()
            and self.__observer.is_alive()
        )
