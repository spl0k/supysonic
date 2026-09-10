# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from urllib.parse import urlparse

from playhouse.db_url import parseresult_to_dict, schemes

from .migration import create_or_upgrade_schema
from .proxy import db


def init_database(database_uri):
    uri = urlparse(database_uri)
    args = parseresult_to_dict(uri)

    if uri.scheme.startswith("mysql"):
        provider = "mysql"
        args.setdefault("charset", "utf8mb4")
        args.setdefault("binary_prefix", True)
    elif uri.scheme.startswith("postgres"):
        provider = "postgres"
    elif uri.scheme.startswith("sqlite"):
        provider = "sqlite"
        args["pragmas"] = {"foreign_keys": 1}
    else:
        raise RuntimeError(f"Unsupported database: {uri.scheme}")

    db_class = schemes.get(uri.scheme)
    db.initialize(db_class(**args))
    db.connect()

    create_or_upgrade_schema(provider, **args)


def release_database():
    db.close()
    db.initialize(None)


def open_connection(reuse=False):
    return db.connect(reuse)


def close_connection():
    db.close()
