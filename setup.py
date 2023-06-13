# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2021 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path

from shutil import rmtree
from setuptools import setup
from setuptools.command.sdist import sdist as _sdist


class sdist(_sdist):
    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)

        man_dir = os.path.join(base_dir, "man")
        doctrees_dir = os.path.join(man_dir, ".doctrees")
        self.spawn(["sphinx-build", "-q", "-b", "man", "docs", man_dir])
        rmtree(doctrees_dir)


if __name__ == "__main__":
    setup(
        cmdclass={"sdist": sdist},
    )
