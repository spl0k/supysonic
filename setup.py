#!/usr/bin/python
# encoding: utf-8

from distutils.core import setup

setup(name='supysonic',
      description='Python implementation of the Subsonic server API.',
      keywords='subsonic music',
      version='0.1',
      url='https://github.com/spl0k/supysonic',
      license='AGPLv3',
      author='Alban Féron',
      author_email='alban.feron@gmail.com',
      long_description="""
      Supysonic is a Python implementation of the Subsonic server API.

      Current supported features are:

      * browsing (by folders or tags)
      * streaming of various audio file formats
      * transcoding
      * user or random playlists
      * cover arts (cover.jpg files in the same folder as music files)
      * starred tracks/albums and ratings
      * Last.FM scrobbling
      """,
      packages=['supysonic', 'supysonic.api', 'supysonic.frontend',
                'supysonic.managers'],
      scripts=['bin/supysonic-cli', 'bin/supysonic-watcher'],
      package_data={'supysonic': ['templates/*.html']}
      )
