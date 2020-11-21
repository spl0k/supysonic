# Supysonic

_Supysonic_ is a Python implementation of the [Subsonic][] server API.

![Build Status](https://github.com/spl0k/supysonic/workflows/Package/badge.svg)
[![codecov](https://codecov.io/gh/spl0k/supysonic/branch/master/graph/badge.svg)](https://codecov.io/gh/spl0k/supysonic)
![Python](https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7%2C%203.8-blue.svg)

Current supported features are:
* browsing (by folders or tags)
* streaming of various audio file formats
* [transcoding]
* user or random playlists
* cover arts (as image files in the same folder as music files)
* starred tracks/albums and ratings
* [Last.FM][lastfm] scrobbling
* Jukebox mode

_Supysonic_ currently targets the version 1.10.2 of the _Subsonic_ API. For more
details, go check the [API implementation status][docs-api].

[subsonic]: http://www.subsonic.org/
[transcoding]: docs/transcoding.md
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
  + [Docker](#docker)
* [Quickstart](#quickstart)
* [Running the daemon](#running-the-daemon)
* [Upgrading](#upgrading)

## Installation

_Supysonic_ can run as a standalone application (not recommended for a
"production" server) or as a WSGI application (on _Apache_ for instance).

To install it, either run:

    $ python setup.py install

or

    $ pip install .

but not both.

### Prerequisites

You'll need Python 3.5 or later to run _Supysonic_.

All the dependencies will automatically be installed by the installation
command above.

You may also need a database specific package if you don't want to use SQLite
(the default):

* _MySQL_: `pip install pymysql` or `pip install mysqlclient`
* _PostgreSQL_: `pip install psycopg2-binary`

### Database initialization

_Supysonic_ needs a database to run. It can either be a _SQLite_,
_MySQL_-compatible or _PostgreSQL_ database.

Please refer to the documentation of the DBMS you've chosen on how to create a
database. Once it has a database, _Supysonic_ will automatically create the
tables it needs.

If you want to use _PostgreSQL_ you'll have to add the `citext` extension to the
database once created. This can be done when connected to the database as the
superuser with the folowing SQL command:

    supysonic=# CREATE EXTENSION citext;

If you absolutely have no clue about databases, you can go with _SQLite_ as it
doesn't need any setup other than specifying a path for the database.
Note that using _SQLite_ for large libraries might not be the brightest idea as
it tends to struggle with larger datasets.

### Configuration

Once you have a database, you'll need to create a configuration file. It must
be saved under one of the following paths:

* `/etc/supysonic`
* `~/.supysonic`
* `~/.config/supysonic/supysonic.conf`

A roughly documented sample configuration file is provided as `config.sample`.

The minimal configuration using a _SQLite_ database would be:

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

    $ apt install libapache2-mod-wsgi-py3
    $ a2enmod wsgi

Next, edit the _Apache_ configuration to load the application. Here's a basic
example of what it looks like:

    WSGIScriptAlias /supysonic /path/to/supysonic/cgi-bin/supysonic.wsgi
    <Directory /path/to/supysonic/cgi-bin>
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Require all granted
    </Directory>

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

### Docker

If you want to run _Supysonic_ in a _Docker_ container, here are some images
provided by the community.

- https://github.com/ultimate-pms/docker-supysonic
- https://github.com/ogarcia/docker-supysonic
- https://github.com/foosinn/supysonic
- https://github.com/mikafouenski/docker-supysonic
- https://github.com/oakman/supysonic-docker
- https://github.com/glogiotatidis/supysonic-docker

## Quickstart

To start using _Supysonic_, you'll first have to specify where your music
library is located and create a user to allow calls to the API.

Let's start by creating a new admin user this way:

    $ supysonic-cli user add MyUserName -p MyAwesomePassword
    $ supysonic-cli user setroles -A MyUserName

To add a new folder to your music library, you can do something like this:

    $ supysonic-cli folder add MyLibrary /home/username/Music

Once you've added a folder, you will need to scan it:

    $ supysonic-cli folder scan MyLibrary

You should now be able to enjoy your music with the client of your choice!

For more details on the command-line usage, take a look at the
[documentation][docs-cli].

[docs-cli]: docs/cli.md

## Client authentication

The Subsonic API provides several authentication methods. One of them, known as
_token authentication_ was added with API version 1.13.0. As Supysonic currently
targets API version 1.9.0, the token based method isn't supported. So if your
client offers you the option, you'll have to disable the token based
authentication for it to work.

## Running the daemon

_Supysonic_ comes with an optional daemon service that currently provides the
following features:
- background scans
- library changes detection
- jukebox mode

First of all, the daemon allows running backgrounds scans, meaning you can start
scans from the CLI and do something else while it's scanning (otherwise the scan
will block the CLI until it's done).
Background scans also enable the web UI to run scans, while you have to use the
CLI to do so if you don't run the daemon.

Instead of manually running a scan every time your library changes, the daemon
can listen to any library change and update the database accordingly. This
watcher is started along with the daemon but can be disabled to only keep
background scans.

Finally, the daemon acts as a backend for the jukebox mode, allowing to play
audio on the machine running Supysonic.

The daemon is `supysonic-daemon`, it is a non-exiting process. If you want to
keep it running in background, either use the old `nohup` or `screen` methods,
or start it as a _systemd_ unit (see the very basic _supysonic-daemon.service_
file).

## Upgrading

To upgrade your _Supysonic_ installation, simply re-run the command you used to
install it (either `python setup.py install` or `pip install .`).

Some commits might introduce changes in the database schema. Starting with
commit e84459d6278bfc735293edc19b535c62bc2ccd8d (August 29th, 2018) migrations
will be automatically applied.

If your database was created prior to this date, you'll have to manually apply
unapplied migrations up to the latest. Once done you won't have to worry about
future migrations as they'll be automatically applied.
Migration scripts are provided in the `supysonic/schema/migration` folder, named
by the date of commit that introduced the schema changes. There could be both
SQL scripts or Python scripts. The Python scripts require arguments that are
explained when the script is invoked with the `-h` flag.
