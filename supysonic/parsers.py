# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import math
import re

TRUE_VALUES = ("true", "yes", "on", "1")
FALSE_VALUES = ("false", "no", "off", "0")

MAIL_MAX_LENGTH = 256  # matches the VARCHAR(256) in schema/<provider>.sql

_ATOM = r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"  # RFC 5322 atext
_LABEL = r"[a-z0-9]([a-z0-9-]*[a-z0-9])?"  # alphanum + hyphen, but no leading/trailing hyphen
_MAIL_RE = re.compile(
    rf"{_ATOM}(\.{_ATOM})*@{_LABEL}(\.{_LABEL})+",
    re.IGNORECASE,
)


def parse_bool(value):
    """Parse a user-provided boolean.

    Returns None if the value is absent, True or False if it is recognized, and
    raises ValueError otherwise. Recognition is case-insensitive.
    """

    if value is None or value == "":
        return None

    lv = str(value).lower()
    if lv in TRUE_VALUES:
        return True
    if lv in FALSE_VALUES:
        return False

    raise ValueError(f"invalid boolean value: {value!r}")


def _check_bounds(value, min, max):
    if min is not None and value < min:
        raise ValueError(f"{value} is lower than the minimum value of {min}")
    if max is not None and value > max:
        raise ValueError(f"{value} is greater than the maximum value of {max}")

    return value


def parse_int(value, min=None, max=None):
    """Parse a user-provided integer, enforcing optional bounds.

    Returns None if the value is absent, raises ValueError if it isn't a valid
    integer or lies outside of the [min, max] range.
    """

    if value is None or value == "":
        return None

    try:
        i = int(value)
    except ValueError as e:
        raise ValueError("not an integer") from e

    return _check_bounds(i, min, max)


def parse_float(value, min=None, max=None):
    """Same as parse_int, for floats. NaN and infinities are rejected."""

    if value is None or value == "":
        return None

    try:
        f = float(value)
    except ValueError as e:
        raise ValueError("not a number") from e

    if not math.isfinite(f):
        raise ValueError("not a finite number")

    return _check_bounds(f, min, max)


def parse_mail(value):
    """Parse a user-provided email address.

    Returns None if the value is absent or blank, the stripped address if it looks like
    a valid one, and raises ValueError otherwise.
    """

    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    if len(value) > MAIL_MAX_LENGTH:
        raise ValueError(f"longer than {MAIL_MAX_LENGTH} characters")

    if not _MAIL_RE.fullmatch(value):
        raise ValueError("not a valid email address")

    return value


def ensure_str(value):
    """Ensure a value is a string, raising TypeError otherwise."""

    if not isinstance(value, str):
        raise TypeError(f"Expecting string, got {type(value)}")


def ensure_list(value):
    """Ensure a value is a list or a tuple, raising TypeError otherwise."""

    if not isinstance(value, (list, tuple)):
        raise TypeError(f"Expecting list, got {type(value)}")
