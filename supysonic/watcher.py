# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2014  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
from signal import signal, SIGTERM
from threading import Thread, Condition, Timer
from logging.handlers import TimedRotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from supysonic import config, db
from supysonic.scanner import Scanner

OP_SCAN     = 1
OP_REMOVE   = 2
OP_MOVE     = 4
FLAG_CREATE = 8

class SupysonicWatcherEventHandler(PatternMatchingEventHandler):
	def __init__(self, queue, logger):
		extensions = config.get('base', 'scanner_extensions')
		patterns = map(lambda e: "*." + e.lower(), extensions.split()) if extensions else None
		super(SupysonicWatcherEventHandler, self).__init__(patterns = patterns, ignore_directories = True)

		self.__queue = queue
		self.__logger = logger

	def dispatch(self, event):
		try:
			super(SupysonicWatcherEventHandler, self).dispatch(event)
		except Exception, e:
			self.__logger.critical(e)

	def on_created(self, event):
		self.__logger.debug("File created: '%s'", event.src_path)
		self.__queue.put(event.src_path, OP_SCAN | FLAG_CREATE)

	def on_deleted(self, event):
		self.__logger.debug("File deleted: '%s'", event.src_path)
		self.__queue.put(event.src_path, OP_REMOVE)

	def on_modified(self, event):
		self.__logger.debug("File modified: '%s'", event.src_path)
		self.__queue.put(event.src_path, OP_SCAN)

	def on_moved(self, event):
		self.__logger.debug("File moved: '%s' -> '%s'", event.src_path, event.dest_path)
		self.__queue.put(event.dest_path, OP_MOVE, src_path = event.src_path)

class Event(object):
	def __init__(self, path, operation, **kwargs):
		if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
			raise Exception("Flags SCAN and REMOVE both set")

		self.__path = path
		self.__time = time.time()
		self.__op = operation
		self.__src = kwargs.get("src_path")

	def set(self, operation, **kwargs):
		if operation & (OP_SCAN | OP_REMOVE) == (OP_SCAN | OP_REMOVE):
			raise Exception("Flags SCAN and REMOVE both set")

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
	def __init__(self, logger):
		super(ScannerProcessingQueue, self).__init__()

		self.__logger = logger
		self.__cond = Condition()
		self.__timer = None
		self.__queue = {}
		self.__running = True

	def run(self):
		try:
			self.__run()
		except Exception, e:
			self.__logger.critical(e)

	def __run(self):
		while self.__running:
			time.sleep(0.1)

			with self.__cond:
				self.__cond.wait()

				if not self.__queue:
					continue

			self.__logger.debug("Instantiating scanner")
			store = db.get_store(config.get('base', 'database_uri'))
			scanner = Scanner(store)

			item = self.__next_item()
			while item:
				if item.operation & OP_MOVE:
					self.__logger.info("Moving: '%s' -> '%s'", item.src_path, item.path)
					scanner.move_file(item.src_path, item.path)
				if item.operation & OP_SCAN:
					self.__logger.info("Scanning: '%s'", item.path)
					scanner.scan_file(item.path)
				if item.operation & OP_REMOVE:
					self.__logger.info("Removing: '%s'", item.path)
					scanner.remove_file(item.path)
				item = self.__next_item()

			scanner.finish()
			store.commit()
			store.close()
			self.__logger.debug("Freeing scanner")
			del scanner

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
			self.__timer = Timer(5, self.__wakeup)
			self.__timer.start()

	def __wakeup(self):
		with self.__cond:
			self.__cond.notify()
			self.__timer = None

	def __next_item(self):
		with self.__cond:
			if not self.__queue:
				return None

			next = min(self.__queue.iteritems(), key = lambda i: i[1].time)
			if not self.__running or next[1].time + 5 <= time.time():
				del self.__queue[next[0]]
				return next[1]

			return None

class SupysonicWatcher(object):
	def run(self):
		if not config.check():
			return

		logger = logging.getLogger(__name__)
		if config.get('daemon', 'log_file'):
			log_handler = TimedRotatingFileHandler(config.get('daemon', 'log_file'), when = 'midnight')
		else:
			log_handler = logging.NullHandler()
		log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
		logger.addHandler(log_handler)
		if config.get('daemon', 'log_level'):
			mapping = {
				'DEBUG':   logging.DEBUG,
				'INFO':    logging.INFO,
				'WARNING': logging.WARNING,
				'ERROR':   logging.ERROR,
				'CRTICAL': logging.CRITICAL
			}
			logger.setLevel(mapping.get(config.get('daemon', 'log_level').upper(), logging.NOTSET))

		store = db.get_store(config.get('base', 'database_uri'))
		folders = store.find(db.Folder, db.Folder.root == True)

		if not folders.count():
			logger.info("No folder set. Exiting.")
			store.close()
			return

		queue = ScannerProcessingQueue(logger)
		handler = SupysonicWatcherEventHandler(queue, logger)
		observer = Observer()

		for folder in folders:
			logger.info("Starting watcher for %s", folder.path)
			observer.schedule(handler, folder.path, recursive = True)

		store.close()
		signal(SIGTERM, self.__terminate)

		self.__running = True
		queue.start()
		observer.start()
		while self.__running:
			time.sleep(2)

		logger.info("Stopping watcher")
		observer.stop()
		observer.join()
		queue.stop()
		queue.join()

	def stop(self):
		self.__running = False

	def __terminate(self, signum, frame):
		self.stop()

