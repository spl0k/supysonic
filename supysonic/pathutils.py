# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path

_SEPARATORS = os.sep + (os.altsep or "")


def _dir_prefix(path):
    """Return `path` with exactly one trailing separator, the prefix shared by
    everything below it. "/" stays "/", "C:\\" stays "C:\\"."""

    return path.rstrip(_SEPARATORS) + os.sep


def is_subpath(path, parent):
    """Tell whether `path` is `parent` itself or lies below it.

    Unlike a plain `startswith`, the comparison happens on path component
    boundaries, so "/music2" isn't considered to be inside "/music".
    """

    parent = parent.rstrip(_SEPARATORS)
    if path.rstrip(_SEPARATORS) == parent:
        return True

    # Any separator will do here: unlike the database, paths reaching this are
    # not necessarily normalized to os.sep
    return path.startswith(parent) and path[len(parent)] in _SEPARATORS


def subpath_expr(field, parent):
    """Build the `is_subpath` equivalent as a peewee expression, matching rows
    whose `field` holds `parent` itself or a path below it."""

    return (field == parent) | field.startswith(_dir_prefix(parent))
