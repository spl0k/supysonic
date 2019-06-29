# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from ..testbase import TestBase


class FrontendTestBase(TestBase):
    __with_webui__ = True

    def setUp(self):
        super(FrontendTestBase, self).setUp()
        self._patch_client()

    def _login(self, username, password):
        return self.client.post(
            "/user/login",
            data={"user": username, "password": password},
            follow_redirects=True,
        )

    def _logout(self):
        return self.client.get("/user/logout", follow_redirects=True)
