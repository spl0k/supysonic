#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import supysonic as project

from setuptools import setup
from setuptools import find_packages
from pip.download import PipSession

try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements


setup(
        name=project.NAME,
        version=project.VERSION,
        description=project.DESCRIPTION,
        keywords=project.KEYWORDS,
        long_description=project.LONG_DESCRIPTION,
        author=project.AUTHOR_NAME,
        author_email=project.AUTHOR_EMAIL,
        url=project.URL,
        license=project.LICENSE,
        packages=find_packages(),
        install_requires=[str(x.req) for x in
            parse_requirements('requirements.txt', session=PipSession())],
        scripts=['bin/supysonic-cli', 'bin/supysonic-watcher'],
        zip_safe=False,
        include_package_data=True,
        test_suite="tests.suite",
        tests_require = [ 'lxml' ],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Console',
            'Environment :: Web Environment',
            'Framework :: Flask',
            'Intended Audience :: End Users/Desktop',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU Affero General Public License v3',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Topic :: Multimedia :: Sound/Audio'
        ]
     )

