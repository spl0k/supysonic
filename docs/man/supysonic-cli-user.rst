==================
supysonic-cli-user
==================

----------------------------------
Supysonic user management commands
----------------------------------

:Author: Louis-Philippe Véronneau
:Date: 2019
:Manual section: 1

Synopsis
========

| supysonic-cli user **add** <user> [-p <password>] [-e <email>]
| supysonic-cli user **delete** <user>
| supysonic-cli user **changepass** <user> <password>
| supysonic-cli user **list**
| supysonic-cli user **setroles** [-a|-A] [-j|-J] <user>

Arguments
=========

| **add**         Add a new user
| **delete**      Delete the user
| **changepass**  Change the user's password
| **list**        List all the users
| **setroles**    Give or remove rights to the user

Options
=======

| **-p** | **--password** *<password>*
|     Specify the user's password

| **-e** | **--email** *<email>*
|     Specify the user's email

| **-a** | **--noadmin**
|     Revoke admin rights

| **-A** | **--admin**
|     Grant admin rights

| **-j** | **--nojukebox**
|     Revoke jukebox rights

| **-J** | **--jukebox**
|     Grant jukebox rights

Examples
========

To add a new admin user::

      $ supysonic-cli user add MyUserName -p MyAwesomePassword
      $ supysonic-cli user setroles -A MyUserName

See Also
========

supysonic-cli(1), supysonic-cli-folder(1)
