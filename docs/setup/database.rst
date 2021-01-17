Database setup
==============

Supysonic needs a database to run. It can either be a SQLite, MySQL-compatible
or PostgreSQL database.

If you absolutely have no clue about databases, you can go with SQLite as it
doesn't need any setup other than specifying a path for the database in the
:doc:`configuration <configuration>`.

.. note::

   SQLite, while being a viable option, isn't recommended for large
   installations. First of all its performance *might* start to decrease as the
   size of your library grows. But most importantly if you have a lot of users
   reaching the instance at the same time you will start to see the performance
   drop, or even errors.

Please refer to the documentation of the DBMS you've chosen on how to create a
database. Once it has a database, Supysonic will automatically create the
tables it needs and keep the schema up-to-date.

The PostgreSQL case
-------------------

If you want to use PostgreSQL you'll have to add the ``citext`` extension to the
database once created. This can be done when connected to the database as the
superuser. How to connect as a superuser might change depending on your
PostgreSQL installation (this is **not** the same thing as the OS superuser
known as *root* on Linux systems).

On a Debian-based system you can connect as a superuser by invoking
:command:`psql` while being logged in as the *postgres* user. The following
commands will install the ``citext`` extension on the database named *supysonic*
assuming you are currently logged as *root*. ::

   # su - postgres
   $ psql supysonic
   supysonic=# CREATE EXTENSION citext;
