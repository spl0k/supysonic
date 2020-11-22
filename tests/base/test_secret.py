# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import shutil
import tempfile

from supysonic.db import init_database, release_database
from supysonic.web import create_application

from ..testbase import TestConfig


class SecretTestCase(unittest.TestCase):
    def setUp(self):
        self.__dir = tempfile.mkdtemp()
        self.config = TestConfig(False, False)
        self.config.BASE["database_uri"] = "sqlite://"
        self.config.WEBAPP["cache_dir"] = self.__dir

        init_database(self.config.BASE["database_uri"])
        release_database()

    def tearDown(self):
        shutil.rmtree(self.__dir)

    def test_key(self):
        app1 = create_application(self.config)
        release_database()

        app2 = create_application(self.config)
        release_database()

        self.assertEqual(app1.secret_key, app2.secret_key)


if __name__ == "__main__":
    unittest.main()
