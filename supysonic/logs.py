# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger(__package__)

LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

__handlers = []


def setup_logging(config, *, fallback_to_stderr=False):
    """Configure the Supysonic logger from a config section.

    :param config: a config section carrying the ``LoggingOptions``, that is
        ``log_file``, ``log_rotate`` and ``log_level``.
    :param fallback_to_stderr: when no ``log_file`` is set, log to stderr
        instead of not logging at all.
    """
    global __handlers

    for handler in __handlers:
        logger.removeHandler(handler)
        handler.close()
    __handlers = []

    handler = None
    logfile = config.log_file
    if logfile:
        if config.log_rotate:
            handler = TimedRotatingFileHandler(logfile, when="midnight")
        else:
            handler = logging.FileHandler(logfile)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
    elif fallback_to_stderr:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    if handler is not None:
        logger.addHandler(handler)
        __handlers.append(handler)

    loglevel = config.log_level
    if loglevel:
        level = LEVELS.get(loglevel.upper())
        logger.setLevel(logging.NOTSET if level is None else level)
        if level is None:
            logger.warning("Unknown log level %r, leaving it unset", loglevel)
