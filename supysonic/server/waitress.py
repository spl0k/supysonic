# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from waitress import serve

from ._base import BaseServer


class WaitressServer(BaseServer):
    def _build_kwargs(self):
        rv = {"app": self._load_app()}

        if self._host is not None:
            rv["host"] = self._host
        if self._port is not None:
            rv["port"] = self._port
        if self._socket is not None:
            rv["unix_socket"] = self._socket
        if self._threads is not None:
            rv["threads"] = self._threads

        return rv

    def _run(self, **kwargs):
        return serve(**kwargs)


server = WaitressServer
