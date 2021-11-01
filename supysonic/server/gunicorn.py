# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from gunicorn.app.base import BaseApplication

from ._base import BaseServer


class GunicornApp(BaseApplication):
    def __init__(self, app, **config):
        self.__app = app
        self.__config = config

        super().__init__()

    def load(self):
        return self.__app

    def load_config(self):
        socket = self.__config["socket"]
        host = self.__config["host"]
        port = self.__config["port"]
        processes = self.__config["processes"]
        threads = self.__config["threads"]

        if socket is not None:
            self.cfg.set("bind", "unix:{}".format(socket))
        else:
            self.cfg.set("bind", "{}:{}".format(host, port))

        if processes is not None:
            self.cfg.set("workers", processes)
        if threads is not None:
            self.cfg.set("threads", threads)


class GunicornServer(BaseServer):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.__server = GunicornApp(app, **kwargs)

    def _build_kwargs(self):
        return {}

    def _run(self, **kwargs):
        return self.__server.run()


server = GunicornServer
