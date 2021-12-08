supysonic-cli
=============

SYNOPSIS
--------

supysonic-cli *--help*

supysonic-cli **user** [*options*]

supysonic-cli **folder** [*options*]

DESCRIPTION
-----------

Supysonic is a Python implementation of the Subsonic server API.
Current supported features are:

* browsing (by folders or tags)
* streaming of various audio file formats
* transcoding
* user or random playlists
* cover arts (as image files in the same folder as music files)
* starred tracks/albums and ratings
* Last.FM scrobbling
* Jukebox mode

The "Subsonic API" is a set of adhoc standards to browse, stream or download a
music collection over HTTP.

The command-line interface is an interface allowing administration operations
without the use of the web interface.

SUBCOMMANDS
-----------

supysonic-cli has two different subcommands:

**user** [*options*]
    User management commands

**folder** [*options*]
   Folder management commands

For more details on the **user** and **folder** subcommands, see the
``subsonic-cli-user (1)``, ``subsonic-cli-folder (1)`` manual pages.

OPTIONS
-------

**-h**, **--help**
    Shows the help and exits. At top level it only lists the subcommands. To
    display the help of a specific subcommand, add the **--help** flag *after*
    the said subcommand name.

BUGS
----

Bugs can be reported to your distribution's bug tracker or upstream
at https://github.com/spl0k/supysonic/issues.

SEE ALSO
--------

``supysonic-cli-user (1)``, ``supysonic-cli-folder (1)``,
``supysonic-server (1)``, ``supysonic-daemon (1)``
