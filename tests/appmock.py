# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
from flask import Flask
from supysonic.db import get_store

class AppMock(object):
    def __init__(self, with_store = True):
        self.app = Flask(__name__, template_folder = '../supysonic/templates')
        self.app.testing = True
        self.app.secret_key = 'Testing secret'

        if with_store:
            self.store = get_store('sqlite:')
            with io.open('schema/sqlite.sql', 'r') as sql:
                schema = sql.read()
                for statement in schema.split(';'):
                    self.store.execute(statement)
        else:
            self.store = None

