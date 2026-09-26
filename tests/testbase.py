# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import os.path
import shlex
import shutil
import sys
import tempfile
import unittest
from contextlib import suppress

from peewee import MySQLDatabase, PostgresqlDatabase

from supysonic.config import Config
from supysonic.db import db, init_database, release_database
from supysonic.db.exceptions import (
    DatabaseAlreadyInitializedError,
    DatabaseNotInitializedError,
)
from supysonic.web import create_application

# When set, the whole test suite runs against this database instead of the
# default throwaway SQLite. Since a MySQL/PostgreSQL server is shared across all
# tests (unlike the per-test SQLite file), rows are truncated between tests to
# keep them isolated. See get_test_db_uri()/teardown_test_db().
TEST_DB_URI = os.environ.get("SUPYSONIC_TEST_DB_URI")


def get_test_db_uri(memory=False):
    """Return ``(uri, tmp)`` describing the database to use for a test.

    When ``SUPYSONIC_TEST_DB_URI`` is set that URI is used and ``tmp`` is
    ``None``. Otherwise an SQLite database is used: an in-memory one when
    ``memory`` is true, else a temporary file whose ``mkstemp`` handle is
    returned as ``tmp`` so the caller can clean it up through
    :func:`teardown_test_db`.
    """
    if TEST_DB_URI:
        return TEST_DB_URI, None
    if memory:
        return "sqlite:", None
    tmp = tempfile.mkstemp()
    return "sqlite:///" + tmp[1], tmp


def teardown_test_db(tmp):
    """Clean up the database after a test.

    On a shared (non-SQLite) server the schema is kept but every table except
    ``meta`` is truncated so the next test starts from a clean state; ``meta``
    is preserved because :func:`~supysonic.db.init_database` relies on it to
    detect an already-initialized database. Finally the database is released and
    any SQLite temporary file (``tmp``) is removed.
    """
    if TEST_DB_URI:
        # Make sure the database is bound, some tests might release it
        with suppress(DatabaseAlreadyInitializedError):
            init_database(TEST_DB_URI)
        _truncate_tables()

    # and also handle tests that already released it
    with suppress(DatabaseNotInitializedError):
        release_database()

    if tmp is not None:
        os.close(tmp[0])
        os.remove(tmp[1])


def _truncate_tables():
    if db.is_closed():
        db.connect()

    tables = [t for t in db.get_tables() if t != "meta"]
    if not tables:
        return

    if isinstance(db.obj, PostgresqlDatabase):
        quoted = ", ".join(f'"{t}"' for t in tables)
        db.execute_sql(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
    elif isinstance(db.obj, MySQLDatabase):
        db.execute_sql("SET FOREIGN_KEY_CHECKS=0")
        for t in tables:
            db.execute_sql(f"TRUNCATE `{t}`")
        db.execute_sql("SET FOREIGN_KEY_CHECKS=1")
    else:
        # SQLite: PRAGMA foreign_keys can only be toggled outside a transaction.
        db.execute_sql("PRAGMA foreign_keys=OFF")
        for t in tables:
            db.execute_sql(f'DELETE FROM "{t}"')
        db.execute_sql("PRAGMA foreign_keys=ON")


# Cross-platform fake transcoders driven by a small Python helper invoked through
# sys.executable (see tests/transcoding_tools.py), so the transcoding tests run on
# every platform instead of relying on Unix-only tools (echo, dd, cat, md5sum).
_TOOL = os.path.join(os.path.dirname(__file__), "transcoding_tools.py")


def _tool_cmd(*args):
    # shlex.quote round-trips through the shlex.split done in
    # prepare_transcoding_cmdline (POSIX mode preserves Windows backslashes when
    # single-quoted), so the interpreter and helper paths survive intact.
    return " ".join(shlex.quote(p) for p in (sys.executable, _TOOL, *args))


def _merge_sections(base, extra):
    merged = {name: dict(options) for name, options in base.items()}
    for name, options in extra.items():
        merged.setdefault(name, {}).update(options)

    return merged


def TestConfig(with_webui, with_api, **sections):
    """Build a Config suitable for tests.

    Keyword arguments are extra section contents merged into the defaults below,
    e.g. ``TestConfig(False, False, base={"database_uri": uri})``.
    """

    with tempfile.NamedTemporaryFile() as tf:
        if sys.platform == "win32":
            socket = "\\\\.\\pipe\\" + os.path.basename(tf.name)
        else:
            socket = tf.name

    raw = _merge_sections(
        {
            "webapp": {"mount_webui": with_webui, "mount_api": with_api},
            "daemon": {"socket": socket},
            "mimetypes": {
                "mp3": "audio/mpeg",
                "weirdextension": "application/octet-stream",
            },
            "transcoding": {
                "transcoder_mp3_mp3": _tool_cmd("echo", "%srcpath", "%outrate"),
                "transcoder_mp3_rnd": _tool_cmd("urandom", "52000"),
                "decoder_mp3": _tool_cmd("decode"),
                "encoder_cat": _tool_cmd("cat"),
                "encoder_md5": _tool_cmd("md5"),
            },
        },
        sections,
    )

    return Config(raw)


class MockResponse:
    def __init__(self, response):
        self.__status_code = response.status_code
        self.__data = response.get_data(as_text=True)
        self.__mimetype = response.mimetype

    @property
    def status_code(self):
        return self.__status_code

    @property
    def data(self):
        return self.__data

    @property
    def mimetype(self):
        return self.__mimetype


def patch_method(f):
    original = f

    def patched(*args, **kwargs):
        rv = original(*args, **kwargs)
        return MockResponse(rv)

    return patched


class TestBase(unittest.TestCase):
    __with_webui__ = False
    __with_api__ = False

    # Extra config section contents, merged into the ones below by subclasses
    # needing the app to be built with a specific option set
    __sections__ = {}

    def setUp(self):
        uri, self.__db = get_test_db_uri()
        self.__dir = tempfile.mkdtemp()
        self.config = TestConfig(
            self.__with_webui__,
            self.__with_api__,
            **_merge_sections(
                {
                    "base": {"database_uri": uri},
                    "webapp": {"cache_dir": self.__dir},
                },
                self.__sections__,
            ),
        )

        self.__app = create_application(self.config, testing=True)
        self._app_layer = self.__app.extensions["supysonic"]
        self.client = self.__app.test_client()

        # Hashing uses reduced scrypt work factors here; see tests/__init__.py
        users = self._app_layer.users
        users.add("alice", "Alic3", admin=True)
        users.add("bob", "B0b")

    def _patch_client(self):
        self.client.get = patch_method(self.client.get)
        self.client.post = patch_method(self.client.post)

    def request_context(self, *args, **kwargs):
        return self.__app.test_request_context(*args, **kwargs)

    def tearDown(self):
        teardown_test_db(self.__db)
        shutil.rmtree(self.__dir)
