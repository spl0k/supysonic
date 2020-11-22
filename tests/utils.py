# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import binascii


def hexlify(s):
    return binascii.hexlify(s.encode("utf-8")).decode("utf-8")
