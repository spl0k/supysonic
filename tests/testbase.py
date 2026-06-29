# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import inspect
import os
import os.path
import shlex
import shutil
import sys
import tempfile
import unittest

from supysonic.db import release_database
from supysonic.config import DefaultConfig
from supysonic.managers.user import UserManager
from supysonic.web import create_application


# Cross-platform fake transcoders driven by a small Python helper invoked through
# sys.executable (see tests/transcoding_tools.py), so the transcoding tests run on
# every platform instead of relying on Unix-only tools (echo, dd, cat, md5sum).
_TOOL = os.path.join(os.path.dirname(__file__), "transcoding_tools.py")


def _tool_cmd(*args):
    # shlex.quote round-trips through the shlex.split done in
    # prepare_transcoding_cmdline (POSIX mode preserves Windows backslashes when
    # single-quoted), so the interpreter and helper paths survive intact.
    return " ".join(shlex.quote(p) for p in (sys.executable, _TOOL, *args))


class TestConfig(DefaultConfig):
    TESTING = True
    LOGGER_HANDLER_POLICY = "never"
    MIMETYPES = {"mp3": "audio/mpeg", "weirdextension": "application/octet-stream"}
    TRANSCODING = {
        "transcoder_mp3_mp3": _tool_cmd("echo", "%srcpath", "%outrate"),
        "transcoder_mp3_rnd": _tool_cmd("urandom", "52000"),
        "decoder_mp3": _tool_cmd("decode"),
        "encoder_cat": _tool_cmd("cat"),
        "encoder_md5": _tool_cmd("md5"),
    }

    def __init__(self, with_webui, with_api):
        super().__init__()

        for cls in reversed(inspect.getmro(self.__class__)):
            for attr, value in cls.__dict__.items():
                if attr.startswith("_") or attr != attr.upper():
                    continue

                if isinstance(value, dict):
                    setattr(self, attr, value.copy())
                else:
                    setattr(self, attr, value)

        self.WEBAPP.update({"mount_webui": with_webui, "mount_api": with_api})

        with tempfile.NamedTemporaryFile() as tf:
            if sys.platform == "win32":
                self.DAEMON["socket"] = "\\\\.\\pipe\\" + os.path.basename(tf.name)
            else:
                self.DAEMON["socket"] = tf.name


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

    def setUp(self):
        self.__db = tempfile.mkstemp()
        self.__dir = tempfile.mkdtemp()
        self.config = TestConfig(self.__with_webui__, self.__with_api__)
        self.config.BASE["database_uri"] = "sqlite:///" + self.__db[1]
        self.config.WEBAPP["cache_dir"] = self.__dir

        self.__app = create_application(self.config)
        self.client = self.__app.test_client()

        UserManager.add("alice", "Alic3", admin=True)
        UserManager.add("bob", "B0b")

    def _patch_client(self):
        self.client.get = patch_method(self.client.get)
        self.client.post = patch_method(self.client.post)

    def app_context(self, *args, **kwargs):
        return self.__app.app_context(*args, **kwargs)

    def request_context(self, *args, **kwargs):
        return self.__app.test_request_context(*args, **kwargs)

    def tearDown(self):
        release_database()
        shutil.rmtree(self.__dir)
        os.close(self.__db[0])
        os.remove(self.__db[1])
