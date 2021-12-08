supysonic-daemon
================

SYNOPSIS
--------

supysonic-daemon

DESCRIPTION
-----------

**supysonic-daemon** is an optional non-exiting process made to be ran in the
background to manage background scans, library changes detection and the jukebox
mode (audio played on the server hardware).

If **supysonic-daemon** is running when you start a manual scan using
**supysonic-cli**, the scan will be run by the daemon process in the background
instead of running in the foreground. This daemon also enables the web UI scan
feature.

With proper configuration, **supysonic-daemon** also allows authorized users to
play audio on the machine's hardware, using their client as a remote control.

BUGS
----

Bugs can be reported to your distribution's bug tracker or upstream at
https://github.com/spl0k/supysonic/issues.

SEE ALSO
--------

``supysonic-cli (1)``
