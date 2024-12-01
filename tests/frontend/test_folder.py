# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.db import Folder

from .frontendtestbase import FrontendTestBase


class FolderTestCase(FrontendTestBase):
    def test_index(self):
        self._login("bob", "B0b")
        rv = self.client.get("/folder", follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertNotIn("Music folders", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/folder")
        self.assertIn("Music folders", rv.data)

    def test_add_get(self):
        self._login("bob", "B0b")
        rv = self.client.get("/folder/add", follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertNotIn("Add new folder", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/folder/add")
        self.assertIn("Add new folder", rv.data)

    def test_add_post(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/folder/add")
        self.assertIn("required", rv.data)
        rv = self.client.post("/folder/add", data={"name": "name"})
        self.assertIn("required", rv.data)
        rv = self.client.post("/folder/add", data={"path": "path"})
        self.assertIn("required", rv.data)
        rv = self.client.post("/folder/add", data={"name": "name", "path": "path"})
        self.assertIn("Add new folder", rv.data)
        rv = self.client.post(
            "/folder/add",
            data={"name": "name", "path": "tests/assets"},
            follow_redirects=True,
        )
        self.assertIn("created", rv.data)
        self.assertEqual(Folder.select().count(), 1)

    def test_delete(self):
        folder = Folder.create(name="folder", path="tests/assets", root=True)

        self._login("bob", "B0b")
        rv = self.client.get("/folder/del/" + str(folder.id), follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertEqual(Folder.select().count(), 1)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/folder/del/string", follow_redirects=True)
        self.assertIn("Invalid folder id", rv.data)
        rv = self.client.get("/folder/del/1234567890", follow_redirects=True)
        self.assertIn("No such folder", rv.data)
        rv = self.client.get("/folder/del/" + str(folder.id), follow_redirects=True)
        self.assertIn("Music folders", rv.data)
        self.assertEqual(Folder.select().count(), 0)

    def test_scan(self):
        folder = Folder.create(name="folder", path="tests/assets/folder", root=True)

        self._login("alice", "Alic3")

        rv = self.client.get("/folder/scan/string", follow_redirects=True)
        self.assertIn("Invalid folder id", rv.data)
        rv = self.client.get("/folder/scan/1234567890", follow_redirects=True)
        self.assertIn("No such folder", rv.data)
        rv = self.client.get("/folder/scan/" + str(folder.id), follow_redirects=True)
        self.assertIn("start", rv.data)
        rv = self.client.get("/folder/scan", follow_redirects=True)
        self.assertIn("start", rv.data)


if __name__ == "__main__":
    unittest.main()
