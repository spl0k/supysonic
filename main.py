#!/usr/bin/python
# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import config
import os.path, sys

if __name__ == '__main__':
	if not config.check():
		sys.exit(1)

	if not os.path.exists(config.get('base', 'cache_dir')):
		os.makedirs(config.get('base', 'cache_dir'))

	import db
	from web import app

	db.init_db()
	app.run(host = '0.0.0.0', debug = True)

