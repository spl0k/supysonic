====================
supysonic-cli-folder
====================

------------------------------------
Supysonic folder management commands
------------------------------------

:Author: Louis-Philippe Véronneau
:Date: 2019
:Manual section: 1

Synopsis
========

| supysonic-cli folder **add** <name> <path>
| supysonic-cli folder **delete** <name>
| supysonic-cli folder **list**
| supysonic-cli folder **scan** [-f] [--background | --foreground] [<name>...]

Arguments
=========

| **add**     Add a new folder
| **delete**  Delete a folder
| **list**    List all the folders
| **scan**    Scan all or specified folders

Options
=======

| **-f** | **--force**
|     Force scan of already known files even if they haven't changed

| **--background**
|     Scan in the background. Requires the daemon to be running

| **--foreground**
|     Scan in the foreground, blocking the process while the scan is running

Examples
========

To add a new folder to your music library, you can do something like this::

      $ supysonic-cli folder add MyLibrary /home/username/Music

Once you've added a folder, you will need to scan it::

      $ supysonic-cli folder scan MyLibrary

See Also
========

supysonic-cli(1), supysonic-cli-user(1)
