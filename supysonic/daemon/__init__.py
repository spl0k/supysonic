# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2014-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from logging.handlers import TimedRotatingFileHandler
from signal import signal, SIGTERM, SIGINT

from .client import DaemonClient
from .server import Daemon

from ..config import IniConfig
from ..db import init_database, release_database

__all__ = ["Daemon", "DaemonClient"]

logger = logging.getLogger("supysonic")

daemon = None


def setup_logging(config):
    if config["log_file"]:
        if config["log_rotate"]:
            log_handler = TimedRotatingFileHandler(config["log_file"], when="midnight")
        else:
            log_handler = logging.FileHandler(config["log_file"])
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
    else:
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(log_handler)
    if "log_level" in config:
        level = getattr(logging, config["log_level"].upper(), logging.NOTSET)
        logger.setLevel(level)


def __terminate(signum, frame):
    global daemon

    logger.debug("Got signal %i. Stopping...", signum)
    daemon.terminate()
    release_database()


def main():
    global daemon

    config = IniConfig.from_common_locations()
    setup_logging(config.DAEMON)

    signal(SIGTERM, __terminate)
    signal(SIGINT, __terminate)

    init_database(config.BASE["database_uri"])
    daemon = Daemon(config)
    daemon.run()
