# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import functools
import os.path

from werkzeug.security import generate_password_hash as _werkzeug_password_hash

from supysonic.managers import user as _user_manager

# Werkzeug's default scrypt parameters cost ~68 ms per hash, and the suite
# performs ~1650 of them (two per TestBase.setUp for alice and bob, plus one per
# API request, since the Subsonic API re-authenticates on every call) -- about
# 76% of the suite's runtime. Minimal work factors keep the KDF behaving
# identically while making it cheap: check_password_hash reads the parameters
# back out of the stored hash, so verification follows suit and the legacy-hash
# upgrade path in try_auth is still exercised unchanged.
# Done here rather than in testbase.py so it applies to every test module by way
# of the import machinery, and so this package's __init__ imports no sibling.
_TEST_HASH_METHOD = "scrypt:1024:8:1"

_user_manager.generate_password_hash = functools.partial(
    _werkzeug_password_hash, method=_TEST_HASH_METHOD
)
# Recomputed so the unknown-user branch of try_auth gets cheap too.
_user_manager._DUMMY_HASH = _user_manager.generate_password_hash("dummy")


def load_tests(loader, tests, pattern):
    this_dir = os.path.dirname(__file__)
    tests.addTests(loader.discover(start_dir=this_dir, pattern="test*.py"))
    tests.addTests(loader.discover(start_dir=this_dir, pattern="issue*.py"))
    return tests
