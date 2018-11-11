# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2014-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os.path
import time

from logging.handlers import TimedRotatingFileHandler
from pony.orm import db_session
from signal import signal, SIGTERM, SIGINT
from threading import Thread, Condition, Timer
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from . import covers
from .db import init_database, release_database, Folder
from .py23 import dict
from .scanner import Scanner

OP_SCAN     = 1
OP_REMOVE   = 2
OP_MOVE     = 4
FLAG_CREATE = 8
FLAG_COVER  = 16

logger = logging.getLogger(__name__)

class SupysonicWatcherEventHandler(PatternMatchingEventHandler):
    def __init__(self, extensions, queue):
        patterns = None
        if extensions:
            patterns = list(map(lambda e: "*." + e.lower(), extensions.split())) + list(map(lambda e: "*" + e, covers.EXTENSIONS))
        super(SupysonicWatcherEventHandler, self).__init__(patterns = patterns, ignore_directories = True)

        self.__queue = queue

    def dispatch(self, event):
        try:
            super(SupysonicWatcherEventHandler, self).dispatch(event)
        except Exception as e: # pragma: nocover
            logger.critical(e)

    def on_created(self, event):
        logger.debug("File created: '%s'", event.src_path)

        op = OP_SCAN | FLAG_CREATE
        if not covers.is_valid_cover(event.src_path):
            self.__queue.put(event.src_path, op)

            dirname = os.path.dirname(event.src_path)
            with db_session:
                folder = Folder.get(path = dirname)
            if folder is None:
                self.__queue.put(dirname, op | FLAG_COVER)
        else:
            self.__queue.put(event.src_path, op | FLAG_COVER)

    def on_deleted(self, event):
        logger.debug("File deleted: '%s'", event.src_path)

        op = OP_REMOVE
        _, ext = os.path.splitext(event.src_path)
        if ext in covers.EXTENSIONS:
            op |= FLAG_COVER
        self.__queue.put(event.src_path, op)

    def on_modified(self, event):
        logger.debug("File modified: '%s'", event.src_path)
        if not covers.is_valid_cover(event.src_path):
            self.__queue.put(event.src_path, OP_SCAN)

    def on_moved(self, event):
        logger.debug("File moved: '%s' -> '%s'", event.src_path, event.dest_path)

        op = OP_MOVE
        _, ext = os.path.splitext(event.src_path)
        if ext in covers.EXTENSIONS:
            op |= FLAG_COVER
        self.__queue.put(event.dest_path, op, src_path = event.src_path)

class Event(object):
    def __init__(self, path, operation, **kwargs):
        if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
            raise Exception("Flags SCAN and REMOVE both set") # pragma: nocover

        self.__path = path
        self.__time = time.time()
        self.__op = operation
        self.__src = kwargs.get("src_path")

    def set(self, operation, **kwargs):
        if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
            raise Exception("Flags SCAN and REMOVE both set") # pragma: nocover

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
        super(ScannerProcessingQueue, self).__init__()

        self.__timeout = delay
        self.__cond = Condition()
        self.__timer = None
        self.__queue = dict()
        self.__running = True

    def run(self):
        try:
            self.__run()
        except Exception as e: # pragma: nocover
            logger.critical(e)
            raise e

    def __run(self):
        while self.__running:
            time.sleep(0.1)

            with self.__cond:
                self.__cond.wait()

                if not self.__queue:
                    continue

            logger.debug("Instantiating scanner")
            scanner = Scanner()

            item = self.__next_item()
            while item:
                if item.operation & FLAG_COVER:
                    self.__process_cover_item(scanner, item)
                else:
                    self.__process_regular_item(scanner, item)

                item = self.__next_item()

            scanner.finish()
            logger.debug("Freeing scanner")
            del scanner

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
        self.__running = False
        with self.__cond:
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
                event.set(previous.operation, src_path = previous.src_path)
                del self.__queue[kwargs["src_path"]]

            if self.__timer:
                self.__timer.cancel()
            self.__timer = Timer(self.__timeout, self.__wakeup)
            self.__timer.start()

    def __wakeup(self):
        with self.__cond:
            self.__cond.notify()
            self.__timer = None

    def __next_item(self):
        with self.__cond:
            if not self.__queue:
                return None

            next = min(self.__queue.items(), key = lambda i: i[1].time)
            if not self.__running or next[1].time + self.__timeout <= time.time():
                del self.__queue[next[0]]
                return next[1]

            return None

class SupysonicWatcher(object):
    def __init__(self, config):
        self.__config = config
        self.__running = True
        init_database(config.BASE['database_uri'])

    def run(self):
        if self.__config.DAEMON['log_file']:
            log_handler = TimedRotatingFileHandler(self.__config.DAEMON['log_file'], when = 'midnight')
            log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        else:
            log_handler = logging.StreamHandler()
            log_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(log_handler)
        if 'log_level' in self.__config.DAEMON:
            level = getattr(logging, self.__config.DAEMON['log_level'].upper(), logging.NOTSET)
            logger.setLevel(level)

        with db_session:
            folders = Folder.select(lambda f: f.root)
            shouldrun = folders.exists()
        if not shouldrun:
            logger.info("No folder set. Exiting.")
            release_database()
            return

        queue = ScannerProcessingQueue(self.__config.DAEMON['wait_delay'])
        handler = SupysonicWatcherEventHandler(self.__config.BASE['scanner_extensions'], queue)
        observer = Observer()

        with db_session:
            for folder in folders:
                logger.info("Starting watcher for %s", folder.path)
                observer.schedule(handler, folder.path, recursive = True)

        try: # pragma: nocover
            signal(SIGTERM, self.__terminate)
            signal(SIGINT, self.__terminate)
        except ValueError:
            logger.warning('Unable to set signal handlers')

        queue.start()
        observer.start()
        while self.__running:
            time.sleep(2)

        logger.info("Stopping watcher")
        observer.stop()
        observer.join()
        queue.stop()
        queue.join()
        release_database()

    def stop(self):
        self.__running = False

    def __terminate(self, signum, frame):
        self.stop() # pragma: nocover

