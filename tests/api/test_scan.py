# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from time import sleep
from threading import Thread

from supysonic.daemon.server import Daemon
from supysonic.db import Folder

from .apitestbase import ApiTestBase


class ScanTestCase(ApiTestBase):
    def setUp(self):
        super().setUp(apiVersion="1.16.0")

    def test_unauthorized(self):
        self._make_request("startScan", args={"u": "bob", "p": "B0b"}, error=50)
        self._make_request("getScanStatus", args={"u": "bob", "p": "B0b"}, error=50)

    def test_unavailable(self):
        self._make_request("startScan", error=0)
        self._make_request("getScanStatus", error=0)


class ScanWithDaemonTestCase(ApiTestBase):
    def setUp(self):
        super().setUp(apiVersion="1.16.0")

        Folder.create(name="Root", root=True, path="tests/assets")

        self._daemon = Daemon(self.config)
        self._thread = Thread(target=self._daemon.run)
        self._thread.start()
        sleep(0.2)  # Wait a bit for the daemon thread to initialize

    def tearDown(self):
        self._daemon.terminate()
        self._thread.join()

        super().tearDown()

    def test_startScan(self):
        rv, child = self._make_request("startScan", tag="scanStatus", skip_post=True)
        self.assertEqual(child.get("scanning"), "true")
        self.assertGreaterEqual(int(child.get("count")), 0)

    def test_getScanStatus(self):
        rv, child = self._make_request("getScanStatus", tag="scanStatus")
        self.assertEqual(child.get("scanning"), "false")
        self.assertEqual(int(child.get("count")), 0)
