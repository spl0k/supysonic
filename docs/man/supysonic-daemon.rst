================
supysonic-daemon
================

------------------------
Supysonic scanner daemon
------------------------

:Author: Louis-Philippe Véronneau
:Date: 2019
:Manual section: 1

Synopsis
========

| supysonic-daemon

Description
===========

| **supysonic-daemon** is an optional non-exiting process made to be ran in the
| background to manage background scans and library changes detection.

| If **supysonic-daemon** is running when you start a manual scan using
| **supysonic-cli(1)**, the scan will be run by the daemon process in the
| background instead of running in the foreground. This daemon also enables the
| web UI scan feature.

Bugs
====

| Bugs can be reported to your distribution's bug tracker or upstream
| at https://github.com/spl0k/supysonic/issues.

See Also
========

supysonic-cli(1)
