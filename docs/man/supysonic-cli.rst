=============
supysonic-cli
=============

------------------------------------------------
Python implementation of the Subsonic server API
------------------------------------------------

:Author: Louis-Philippe Véronneau
:Date: 2019
:Manual section: 1

Synopsis
========

| supysonic-cli [**subcommand**]
| supysonic-cli **help**
| supysonic-cli **help** *user*
| supysonic-cli **help** *folder*

Description
===========

| supysonic is a Python implementation of the Subsonic server API.
| Current supported features are:

| 

| * browsing (by folders or tags)
| * streaming of various audio file formats
| * transcoding
| * user or random playlists
| * cover arts (as image files in the same folder as music files)
| * starred tracks/albums and ratings
| * Last.FM scrobbling

| The "Subsonic API" is a set of adhoc standards to browse, stream or
| download a music collection over HTTP.

Subcommands
===========

| If ran without arguments, **supysonic-cli** will open an interactive
| prompt.

**supysonic-cli** has three different subcommands:

| 

| * help
| * user
| * folder

| For more details on the **user** and **folder** subcommands, see the
| subsonic-cli-user(1), subsonic-cli-folder(1) manual pages.

Bugs
====

| Bugs can be reported to your distribution's bug tracker or upstream
| at https://github.com/spl0k/supysonic/issues.

See Also
========

supysonic-cli-user(1), supysonic-cli-folder(1)
