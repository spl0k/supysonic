supysonic-cli-folder
====================

SYNOPSIS
--------

supysonic-cli folder *--help*

supysonic-cli folder **list**

supysonic-cli folder **add** <*name*> <*path*>

supysonic-cli folder **delete** <*name*>

supysonic-cli folder **scan** [*--force*] [*--background* | *--foreground*] <*name*>

DESCRIPTION
-----------

The **supysonic-cli folder** subcommand manages your library folders, where the
audio files are located. This allows one to list, add, delete and scan the
folders.

ARGUMENTS
---------

**list**
    List all the folders.

**add** <*name*> <*path*>
    Add a new library folder called <*name*> and located at <*path*>. <*name*>
    must be unique and <*path*> pointing to an existing directory. If
    ``supysonic-daemon`` is running it will start to listen for changes in this
    folder but will not scan files already present in the folder.

**delete** <*name*>
    Delete the folder called <*name*>.

**scan** [*--force*] [*--background* | *--foreground*] <*name*>
    Scan the specified folders. If none is given, all the registered folders
    are scanned.

OPTIONS
-------

**-h**, **--help**
    Shows help and exits. Depending on where this option appears it will either
    list the available commands or display help for a specific command.

**-f**, **--force**
    Force scan of already known files even if they haven't changed. Might be
    useful if an update to supysonic adds new metadata to audio files.

**--background**
    Scan in the background. Requires the ``supysonic-daemon`` to be running.

**--foreground**
    Scan in the foreground, blocking the process while the scan is running.

If neither **--background** nor **--foreground** is provided, supysonic-cli
will try to connect to the daemon to initiate a background scan, falling back
to a foreground scan if it isn't available.

EXAMPLES
--------

To add a new folder to your music library, you can do something like this::

   $ supysonic-cli folder add MyLibrary /home/username/Music

Once you've added a folder, you will need to scan it::

   $ supysonic-cli folder scan MyLibrary

The audio files residing in ``/home/username/Music`` will now appear under the
``MyLibrary`` folder on the clients.

SEE ALSO
--------

``supysonic-cli (1)``, ``supysonic-cli-user (1)``,
``supysonic-server (1)``, ``supysonic-daemon (1)``
