# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

try:
    # Python 2
    strtype = basestring

    _builtin_dict = dict

    class DictMeta(type):
        def __instancecheck__(cls, instance):
            return isinstance(instance, _builtin_dict)

    class dict(dict):
        __metaclass__ = DictMeta

        def keys(self):
            return self.viewkeys()

        def values(self):
            return self.viewvalues()

        def items(self):
            return self.viewitems()

except NameError:
    # Python 3
    strtype = str
    dict = dict
