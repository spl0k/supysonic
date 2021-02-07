==================
supysonic-cli-user
==================

----------------------------------
Supysonic user management commands
----------------------------------

:Author: Louis-Philippe Véronneau, Alban Féron
:Date: 2019, 2021
:Manual section: 1

Synopsis
========

| ``supysonic-cli user list``
| ``supysonic-cli user add`` `user` [``--password`` `password`] [``--email`` `email`]
| ``supysonic-cli user delete`` `user`
| ``supysonic-cli user changepass`` `user` `password`
| ``supysonic-cli user setroles`` [``--admin``\|\ ``--noadmin``] [``--jukebox``\|\ ``--nojukebox``] `user`
| ``supysonic-cli user rename`` `user` `newname`

Description
===========

The ``supysonic-cli user`` subcommand manages users, allowing to list them, add
a new user, delete an existing user, and change their password or roles.

``supysonic-cli user list``
   List all the users.

``supysonic-cli user add`` `user` [``--password`` `password`] [``--email`` `email`]
   Add a new user named `user`. Will prompt for a password if it isn't given
   with the ``--password`` option.

``supysonic-cli user delete`` `user`
   Delete the user `user`.

``supysonic-cli user changepass`` `user` [`password`]
   Change the password of user `user`. Will prompt for the new password if not
   provided.

``supysonic-cli user setroles`` [``--admin``\|\ ``--noadmin``] [``--jukebox``\|\ ``--nojukebox``] `user`
   Give or remove rights to user `user`.

``supysonic-cli user rename`` `user` `newname`
   Rename the user `user` to `newname`

Options
=======

-p password, --password password
   Specify the user's password upon creation.

-e email, --email email
   Specify the user's email.

The next options relate to user roles. They work in pairs, one option granting
a right while the other revokes it; obviously options of the same pair are
mutually exclusive. The long options are named with the matching right, prefix
it with a ``no`` to revoke the right. For short options, the upper case letter
grants the right while the lower case letter revokes it. Short options might be
combined into a single one such as ``-aJ`` to both revoke the admin right and
grant the jukebox one.

-A, --admin
   Grant admin rights.

-a, --noadmin
   Revoke admin rights.

-J, --jukebox
   Grant jukebox rights.

-j, --nojukebox
   Revoke jukebox rights.

Examples
========

To add a new admin user named `MyUserName` having password `MyAwesomePassword`::

   $ supysonic-cli user add MyUserName -p MyAwesomePassword
   $ supysonic-cli user setroles -A MyUserName

See Also
========

``supysonic-cli``\ (1), ``supysonic-cli-folder``\ (1)
