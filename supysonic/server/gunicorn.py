# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from gunicorn.app.base import BaseApplication

from ._base import BaseServer


class GunicornApp(BaseApplication):
    def __init__(self, **config):
        self.__config = config

        super().__init__()

    def load_config(self):
        socket = self.__config["socket"]
        host = self.__config["host"]
        port = self.__config["port"]
        processes = self.__config["processes"]
        threads = self.__config["threads"]

        if socket is not None:
            self.cfg.set("bind", f"unix:{socket}")
        else:
            self.cfg.set("bind", f"{host}:{port}")

        if processes is not None:
            self.cfg.set("workers", processes)
        if threads is not None:
            self.cfg.set("threads", threads)


class GunicornServer(BaseServer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__server = GunicornApp(**kwargs)
        self.__server.load = self._load_app

    def _build_kwargs(self):
        return {}

    def _run(self, **kwargs):
        return self.__server.run()


server = GunicornServer
