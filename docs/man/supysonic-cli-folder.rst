====================
supysonic-cli-folder
====================

------------------------------------
Supysonic folder management commands
------------------------------------

:Author: Louis-Philippe Véronneau, Alban Féron
:Date: 2019, 2021
:Manual section: 1

Synopsis
========

| ``supysonic-cli folder list``
| ``supysonic-cli folder add`` `name` `path`
| ``supysonic-cli folder delete`` `name`
| ``supysonic-cli folder scan`` [``--force``] [``--background``\|\ ``--foreground``] [`name`]...

Description
===========

The ``supysonic-cli folder`` subcommand manages your library folders, where the
audio files are located. This allows to list, add, delete and scan the folders.

``supysonic-cli folder list``
   List all the folders.

``supysonic-cli folder add`` `name` `path`
   Add a new library folder called `name` and located at `path`. `name` must be
   unique and `path` pointing to an existing directory. If ``supysonic-daemon``
   is running it will start to listen for changes in this folder but will not
   scan files already present in the folder.

``supysonic-cli folder delete`` `name`
   Delete the folder called `name`.

``supysonic-cli folder scan`` [``--force``] [``--background``\|\ ``--foreground``] [`name`]...
   Scan the specified folders. If none is given, all the registered folders are
   scanned.

Options
=======

-f, --force
   Force scan of already known files even if they haven't changed. Might be
   useful if an update to Supysonic adds new metadata to audio files.

--background
   Scan in the background. Requires the ``supysonic-daemon`` to be running

--foreground
   Scan in the foreground, blocking the process while the scan is running

If neither ``--background`` nor ``--foreground`` is provided, ``supysonic-cli``
will try to connect to the daemon to initiate a background scan, falling back to
a foreground scan if it isn't available.

Examples
========

To add a new folder to your music library, you can do something like this::

   $ supysonic-cli folder add MyLibrary /home/username/Music

Once you've added a folder, you will need to scan it::

   $ supysonic-cli folder scan MyLibrary

The audio files residing in `/home/username/Music` will now appear under the
`MyLibrary` folder on the clients.

See Also
========

``supysonic-cli``\ (1), ``supysonic-cli-user``\ (1)
