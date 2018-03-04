#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic.web import create_application
app = create_application()

if __name__ == '__main__':
	if app:
		import sys
		app.run(host = sys.argv[1] if len(sys.argv) > 1 else None, port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000, debug = True)

