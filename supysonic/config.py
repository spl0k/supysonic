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

import os, sys, tempfile, ConfigParser

config = ConfigParser.RawConfigParser({ 'cache_dir': os.path.join(tempfile.gettempdir(), 'supysonic') })

def check():
	try:
		ret = config.read([ '/etc/supysonic/supysonic.conf', os.path.expanduser('~/.supysonic/supysonic.conf') ])
	except (ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError), e:
		print >>sys.stderr, "Error while parsing the configuration file(s):\n%s" % str(e)
		return False

	if not ret:
		print >>sys.stderr, "No configuration file found"
		return False

	try:
		config.get('base', 'database_uri')
	except:
		print >>sys.stderr, "No database URI set"
		return False

	return True

def get(section, name):
	try:
		return config.get(section, name)
	except:
		return None

