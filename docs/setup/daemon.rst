The daemon
==========

Supysonic comes with an optional daemon service that currently provides the
following features:

- background scans
- library changes detection
- jukebox mode

Background scans
----------------

First of all, the daemon allows running backgrounds scans, meaning you can start
scans from the :doc:`command-line interface <../man/supysonic-cli>` and do
something else while it's scanning (otherwise the scan will block the CLI until
it's done). Background scans also enable the web UI to run scans, while you have
to use the CLI to do so if you don't run the daemon.

Library watching
----------------

Instead of manually running a scan every time your library changes, the daemon
can listen to any library change and update the database accordingly. This
watcher is started along with the daemon but can be disabled to only keep
background scans. Please refer to :ref:`conf-daemon` of the configuration to
enable or disable it.

Jukebox
-------

Finally, the daemon acts as a backend for the jukebox mode, allowing to play
audio on the machine running Supysonic. More details on the :doc:`../jukebox`
page.

Running it
----------

The daemon is :doc:`../man/supysonic-daemon`, it is a non-exiting process.
If you want to keep it running in background, either use the old
:command:`nohup` or :command:`screen` methods, or start it as a systemd unit.

Below is a basic service file to load it through systemd. Modify it to match
your installation and save it as
:file:`/etc/systemd/system/supysonic-daemon.service`.

.. code-block:: ini

   [Unit]
   Description=Supysonic Daemon

   [Service]
   User=someuser
   Group=somegroup
   WorkingDirectory=/home/supysonic
   ExecStart=/usr/bin/python3 -m supysonic.daemon

   [Install]
   WantedBy=multi-user.target
