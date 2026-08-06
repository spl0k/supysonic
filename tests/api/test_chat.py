# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.db import ChatMessage

from .apitestbase import ApiTestBase


class ChatTestCase(ApiTestBase):
    def test_add_message(self):
        self._make_request("addChatMessage", error=10)
        rv, child = self._make_request("getChatMessages", tag="chatMessages")
        self.assertEqual(len(child), 0)

        self._make_request(
            "addChatMessage", {"message": "Heres a message"}, skip_post=True
        )
        rv, child = self._make_request("getChatMessages", tag="chatMessages")
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("username"), "alice")
        self.assertEqual(child[0].get("message"), "Heres a message")

    def test_get_messages(self):
        self._make_request("addChatMessage", {"message": "Hello"}, skip_post=True)
        # Backdate the first message
        ChatMessage.update(time=ChatMessage.time - 60).execute()
        self._make_request(
            "addChatMessage", {"message": "Is someone there?"}, skip_post=True
        )

        rv, child = self._make_request("getChatMessages", tag="chatMessages")
        self.assertEqual(len(child), 2)

        since = int(child[1].get("time")) - 500
        rv, child = self._make_request(
            "getChatMessages",
            {"since": since},
            tag="chatMessages",
        )
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get("message"), "Is someone there?")

        self._make_request("getChatMessages", {"since": "invalid timestamp"}, error=0)


if __name__ == "__main__":
    unittest.main()
