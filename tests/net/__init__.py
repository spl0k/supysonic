# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2021 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import os
import os.path
import unittest

from unittest.suite import TestSuite


def load_tests(loader, tests, pattern):
    # Skip these tests from discovery
    return tests


suite = TestSuite()
for e in os.scandir(os.path.dirname(__file__)):
    if not e.name.startswith("test") or not e.name.endswith(".py"):
        continue

    module = importlib.import_module("tests.net." + e.name[:-3])
    tests = unittest.defaultTestLoader.loadTestsFromModule(module)
    suite.addTests(tests)
