# Supysonic

_Supysonic_ is a Python implementation of the [Subsonic][] server API.

[![Build Status](https://travis-ci.org/spl0k/supysonic.svg?branch=master)](https://travis-ci.org/spl0k/supysonic)
[![codecov](https://codecov.io/gh/spl0k/supysonic/branch/master/graph/badge.svg)](https://codecov.io/gh/spl0k/supysonic)
![Python](https://img.shields.io/badge/python-2.7%2C%203.5%2C%203.6-blue.svg)

Current supported features are:
* browsing (by folders or tags)
* streaming of various audio file formats
* [transcoding]
* user or random playlists
* cover arts (`cover.jpg` files in the same folder as music files)
* starred tracks/albums and ratings
* [Last.FM][lastfm] scrobbling

_Supysonic_ currently targets the version 1.8.0 of the _Subsonic_ API. For more
details, go check the [API implementation status][docs-api].

[subsonic]: http://www.subsonic.org/
[transcoding]: docs/trancoding.md
[lastfm]: https://last.fm/
[docs-api]: docs/api.md

## Table of contents

* [Installation](#installation)
  + [Prerequisites](#prerequisites)
  + [Database initialization](#database-initialization)
  + [Configuration](#configuration)
* [Running the application](#running-the-application)
  + [As a standalone debug server](#as-a-standalone-debug-server)
  + [As an Apache WSGI application](#as-an-apache-wsgi-application)
  + [Other options](#other-options)
* [Quickstart](#quickstart)
* [Watching library changes](#watching-library-changes)
* [Upgrading](#upgrading)

## Installation

_Supysonic_ can run as a standalone application (not recommended for a
"production" server) or as a WSGI application (on _Apache_ for instance).
To install it, run:

    $ python setup.py install

### Prerequisites

You'll need these to run _Supysonic_:

* Python 2.7 or >= 3.5
* [Flask](http://flask.pocoo.org/)
* [PonyORM](https://ponyorm.com/)
* [Python Imaging Library](https://github.com/python-pillow/Pillow)
* [requests](http://docs.python-requests.org/)
* [mutagen](https://mutagen.readthedocs.io/en/latest/)
* [watchdog](https://github.com/gorakhargosh/watchdog) (if you want to use the
  [watcher](#watching-library-changes))

You can install all of them using `pip`:

    $ pip install .

You may also need a database specific package:

* _MySQL_: `pip install pymysql` or `pip install mysqlclient`
* _PostgreSQL_: `pip install psycopg2-binary`

### Database initialization

_Supysonic_ needs a database to run. It can either be a _SQLite_,
_MySQL_-compatible or _PostgreSQL_ database.

_Supysonic_ does not automatically create the database and tables it needs to
work. Thus the database and tables must be created prior to running the
application. Please refer to the documentation of the DBMS you've chosen on how
to create a database and how to use a command-line client. If you want to use
_PostgreSQL_ you'll have to add the `citext` extension to the database once
created. This can be done when connected to the database as the superuser with
the folowing SQL command:

    supysonic=# CREATE EXTENSION citext;

Table creation scripts are provided in the `schema` folder for _SQLite_,
_MySQL_ and _PostgreSQL_. Just feed them to any client you're able to use.

If you absolutely have no clue about databases, you can go with _SQLite_.
You'll just need the `sqlite3` command-line tool. Install it and create the
database and tables with the following commands:

    $ apt install sqlite3
    $ sqlite3 /some/path/to/a/supysonic.db < schema/sqlite.sql

Remember the path you've used for the database file
(`/some/path/to/a/supysonic.db` in the example above), you'll need it in the
configuration file.

Note that using _SQLite_ for large libraries might not be the brightest idea as
it tends to struggle with larger datasets.

### Configuration

Once you have a database, you'll need to create a configuration file. It must
be saved under one of the following paths:

* `/etc/supysonic`
* `~/.supysonic`
* `~/.config/supysonic/supysonic.conf`

A roughly documented sample configuration file is provided as `config.sample`.

The minimal configuration using the _SQLite_ database created on the example
above whould be:

```ini
[base]
database_uri = sqlite:////some/path/to/a/supysonic.db
```

For a more details on the configuration, please refer to
[documentation][docs-config].

[docs-config]: docs/configuration.md

## Running the application

### As a standalone debug server

It is possible to run _Supysonic_ as a standalone server, but it is only
recommended to do so if you are hacking on the source. A standalone won't be
able to serve more than one request at a time.

To start the server, just run the `cgi-bin/server.py` script.

    $ python cgi-bin/server.py

By default, it will listen on the loopback interface (`127.0.0.1`) on port
5000, but you can specify another address on the command line, for instance on
all the IPv6 interfaces:

    $ python cgi-bin/server.py ::

### As an _Apache_ WSGI application

_Supysonic_ can run as a WSGI application with the `cgi-bin/supysonic.wsgi`
file. To run it within an _Apache2_ server, first you need to install the WSGI
module and enable it.

    $ apt install libapache2-mod-wsgi
    $ a2enmod wsgi

Next, edit the _Apache_ configuration to load the application. Here's a basic
example of what it looks like:

    WSGIScriptAlias /supysonic /path/to/supysonic/cgi-bin/supysonic.wsgi
    <Directory /path/to/supysonic/cgi-bin>
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Order deny,allow
        Allow from all
    </Directory>

You might also need to run _Apache_ using the system default locale, as the one
it uses might cause problems while scanning the library from the web UI. To do
so, edit the `/etc/apache2/envvars` file, comment the line `export LANG=C` and
uncomment the `. /etc/default/locale` line. Then you can restart _Apache_:

    $ systemctl restart apache2

With that kind of configuration, the server address will look like
*http://server/supysonic/*

### Other options

If you use another HTTP server, such as _nginx_ or _lighttpd_, or prefer to use
FastCGI or CGI over WSGI, FastCGI and CGI scripts are also provided in the
`cgi-bin` folder, respectively as `supysonic.fcgi` and `supysonic.cgi`. You
might need to edit those file to suit your system configuration.

Here are some quick docs on how to configure your server for [FastCGI][] or
[CGI][].

[fastcgi]: http://flask.pocoo.org/docs/deploying/fastcgi/
[cgi]: http://flask.pocoo.org/docs/deploying/cgi/

## Quickstart

To start using _Supysonic_, you'll first have to specify where your music
library is located and create a user to allow calls to the API.

Let's start by creating a new admin user this way:

    $ supysonic-cli user add MyUserName -a -p MyAwesomePassword

To add a new folder to your music library, you can do something like this:

    $ supysonic-cli folder add MyLibrary /home/username/Music

Once you've added a folder, you will need to scan it:

    $ supysonic-cli folder scan MyLibrary

You should now be able to enjoy your music with the client of your choice!

For more details on the command-line usage, take a look at the
[documentation][docs-cli].

[docs-cli]: docs/cli.md

## Watching library changes

Instead of manually running a scan every time your library changes, you can run
a watcher that will listen to any library change and update the database
accordingly.

The watcher is `bin/supysonic-watcher`, it is a non-exiting process and doesn't
print anything to the console. If you want to keep it running in background,
either use the old `nohup` or `screen` methods, or start it as a simple
_systemd_ unit (unit file not included).

It needs some additional dependencies which can be installed with the following
command:

    $ pip install -e .[watcher]

## Upgrading

Some commits might introduce changes in the database schema. When that's the
case migration scripts will be provided in the `schema/migration` folder,
prefixed by the date of commit that introduced the changes. Those scripts
shouldn't be used when initializing a new database, only when upgrading from a
previous schema.

There could be both SQL scripts or Python scripts. The Python scripts require
arguments that are explained when the script is invoked with the `-h` flag.
If a migration script isn't provided for a specific database engine, it simply
means that no migration is needed for this engine.

