#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flup.server.fcgi import WSGIServer
from supysonic.web import create_application

app = create_application()
if app:
	WSGIServer(app, bindAddress = '/path/to/fcgi.sock').run()

