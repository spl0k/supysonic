# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import os.path

from gevent import socket
from gevent.pywsgi import WSGIServer

from ._base import BaseServer


class GeventServer(BaseServer):
    def _build_kwargs(self):
        rv = {"application": self._load_app()}

        if self._socket is not None:
            if os.path.exists(self._socket):
                os.remove(self._socket)

            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(self._socket)
            listener.listen()

            rv["listener"] = listener
        else:
            rv["listener"] = (self._host, self._port)

        return rv

    def _run(self, **kwargs):
        return WSGIServer(**kwargs).serve_forever()


server = GeventServer
