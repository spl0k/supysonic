# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2019 Alban 'spl0k' Féron
#               2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path


def load_tests(loader, tests, pattern):
    this_dir = os.path.dirname(__file__)
    tests.addTests(loader.discover(start_dir=this_dir, pattern="test*.py"))
    tests.addTests(loader.discover(start_dir=this_dir, pattern="issue*.py"))
    return tests
