# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from pony.orm import db_session

from supysonic.db import Folder

from .apitestbase import ApiTestBase

from supysonic.daemon.server import Daemon
from threading import Thread
import logging

logger = logging.getLogger()


class DaemonThread(Thread):
    def __init__(self, daemon):
        super(DaemonThread, self).__init__(target=daemon.run)
        self.daemon = True
        self.start()


class ScanTestCase(ApiTestBase):
    def setUp(self):
        super(ScanTestCase, self).setUp(apiVersion="1.16.0")

        with db_session:
            Folder(name="Root", root=True, path="tests/assets")

    def test_startScan(self):
        self._make_request("startScan", error=0)
        daemon = Daemon(self.config)
        with db_session:
            daemonThread = DaemonThread(daemon)
        rv, child = self._make_request("startScan", tag="scanStatus")
        self.assertTrue(child.get("scanning"))
        self.assertGreaterEqual(int(child.get("count")), 0)
        daemon.terminate()

    def test_getScanStatus(self):
        self._make_request("getScanStatus", error=0)
        daemon = Daemon(self.config)
        with db_session:
            daemonThread = DaemonThread(daemon)
        rv, child = self._make_request("getScanStatus", tag="scanStatus")
        self.assertIn(child.get("scanning"), ["true", "false"])
        self.assertGreaterEqual(int(child.get("count")), 0)
        daemon.terminate()
