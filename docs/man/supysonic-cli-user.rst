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

| supysonic-cli user **add** <user> [-a] [-p <password>] [-e <email>]
| supysonic-cli user **delete** <user>
| supysonic-cli user **changepass** <user> <password>
| supysonic-cli user **list**
| supysonic-cli user **setadmin** [--off] <user>

Arguments
=========

| **add**         Add a new user
| **delete**      Delete the user
| **changepass**  Change the user's password
| **list**        List all the users
| **setadmin**    Give admin rights to the user

Options
=======

| **-a** | **--admin**
|     Create the user with admin rights

| **-p** | **--password** *<password>*
|     Specify the user's password

| **-e** | **--email** *<email>*
|     Specify the user's email

| **--off**
|     Revoke the admin rights if present

Examples
========

To add a new admin user::

      $ supysonic-cli user add MyUserName -a -p MyAwesomePassword

See Also
========

supysonic-cli(1), supysonic-cli-folder(1)
