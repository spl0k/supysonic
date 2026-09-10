# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import importlib.resources
import os.path

from .models import Meta
from .proxy import db

SCHEMA_VERSION = "20260910"

__root_package__ = __package__.partition(".")[0]


def get_resource_text(respath):
    return (
        importlib.resources.files(__root_package__).joinpath(respath).read_text("utf-8")
    )


def list_migrations(provider):
    return (
        e.name
        for e in importlib.resources.files(__root_package__)
        .joinpath(f"schema/migration/{provider}")
        .iterdir()
    )


def execute_sql_resource_script(respath):
    sql = get_resource_text(respath)
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            db.execute_sql(statement)


def create_or_upgrade_schema(provider, **kwargs):
    # Check if we should create the tables
    if not db.table_exists("meta"):
        with db.atomic():
            execute_sql_resource_script(f"schema/{provider}.sql")
            Meta.create(key="schema_version", value=SCHEMA_VERSION)

    # Check for schema changes
    version = Meta["schema_version"]
    if version.value < SCHEMA_VERSION:
        kwargs.pop("pragmas", ())
        migrations = sorted(list_migrations(provider))
        for migration in migrations:
            if migration[0] in ("_", "."):
                continue

            date, ext = os.path.splitext(migration)
            if date <= version.value:
                continue

            if ext == ".sql":
                with db.atomic():
                    execute_sql_resource_script(
                        f"schema/migration/{provider}/{migration}"
                    )
            elif ext == ".py":
                m = importlib.import_module(
                    f".schema.migration.{provider}.{date}", __root_package__
                )
                m.apply(kwargs.copy())

        version.value = SCHEMA_VERSION
        version.save()
