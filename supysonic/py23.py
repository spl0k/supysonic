# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2019 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

# Try built-in scandir, fall back to the package for Python 2.7
try:
    from os import scandir
except ImportError:
    from scandir import scandir

# os.replace was added in Python 3.3, provide a fallback for Python 2.7
try:
    from os import replace as osreplace
except ImportError:
    # os.rename is equivalent to os.replace except on Windows
    # On Windows an existing file will not be overwritten
    # This fallback just attempts to delete the dst file before using rename
    import sys
    if sys.platform != 'win32':
        from os import rename as osreplace
    else:
        import os
        def osreplace(src, dst):
            try:
                os.remove(dst)
            except OSError:
                pass
            os.rename(src, dst)

try:
    from queue import Queue, Empty as QueueEmpty
except ImportError:
    from Queue import Queue, Empty as QueueEmpty

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
