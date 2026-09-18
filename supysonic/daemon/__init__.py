# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2014-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from signal import SIGINT, SIGTERM, signal

from ..config import Config
from ..db.connection import init_database, release_database
from ..logs import setup_logging
from .client import DaemonClient
from .server import Daemon

__all__ = ["Daemon", "DaemonClient"]

logger = logging.getLogger(__name__)

daemon = None


def __terminate(signum, frame):
    global daemon

    logger.debug("Got signal %i. Stopping...", signum)
    daemon.terminate()


def main():
    global daemon

    config = Config.from_common_locations()
    setup_logging(config.daemon, fallback_to_stderr=True)

    signal(SIGTERM, __terminate)
    signal(SIGINT, __terminate)

    init_database(config.base.database_uri)
    daemon = Daemon(config)
    daemon.run()
    release_database()
