# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import os
import os.path

from click import command, option, Option
from click.exceptions import UsageError, ClickException
from click.types import Choice


_servers = [
    e.name[:-3]
    for e in os.scandir(os.path.dirname(__file__))
    if not e.name.startswith("_") and e.name.endswith(".py")
]


class MutuallyExclusiveOption(Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = (
                "{}  NOTE: This argument is mutually exclusive with arguments: [{}].".format(
                    help, ex_str
                )
            )
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise UsageError(
                "Illegal usage: `{}` is mutually exclusive with arguments `{}`.".format(
                    self.name, ", ".join(self.mutually_exclusive)
                )
            )

        return super().handle_parse_result(ctx, opts, args)


def get_server(name):
    return importlib.import_module("." + name, __package__).server


def find_first_available_server():
    for module in _servers:
        try:
            return get_server(module)
        except ImportError:
            pass

    return None


@command()
@option(
    "-S",
    "--server",
    type=Choice(_servers),
    help="Specify which WSGI server to use. Pick the first available if none is set",
)
@option(
    "-h",
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="Hostname or IP address on which to listen",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=("socket",),
)
@option(
    "-p",
    "--port",
    default=5722,
    show_default=True,
    help="TCP port on which to listen",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=("socket",),
)
@option(
    "-s",
    "--socket",
    help="Unix socket on which to bind to, Can't be used with --host and --port",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=("host", "port"),
)
@option(
    "--processes",
    type=int,
    help="Number of processes to spawn. May not be supported by all servers",
)
@option(
    "--threads",
    type=int,
    help="Number of threads used to process application logic. May not be supported by all servers",
)
def main(server, host, port, socket, processes, threads):
    """Starts the Supysonic web server"""

    if server is None:
        server = find_first_available_server()
        if server is None:
            raise ClickException(
                f"Couldn't load any server, please install one of {_servers}"
            )
    else:
        try:
            server = get_server(server)
        except ImportError:
            raise ClickException(f"Couldn't load {server}, please install it first")

    if socket is not None:
        host = None
        port = None

    server(
        host=host, port=port, socket=socket, processes=processes, threads=threads
    ).run()
