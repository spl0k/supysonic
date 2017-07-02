# Supysonic

Supysonic is a Python implementation of the [Subsonic][] server API.

Current supported features are:
* browsing (by folders or tags)
* streaming of various audio file formats
* transcoding
* user or random playlists
* cover arts (`cover.jpg` files in the same folder as music files)
* starred tracks/albums and ratings
* [Last.FM][lastfm] scrobbling

For more details, go check the [API implementation status][api].

[subsonic]: http://www.subsonic.org/
[lastfm]: https://last.fm
[api]: API-INFO.md

## Table of contents

* [Installation](#installation)
  + [Prerequisites](#prerequisites)
  + [Configuration](#configuration)
  + [Database initialization](#database-initialization)
* [Running the application](#running-the-application)
  + [As a standalone debug server](#as-a-standalone-debug-server)
  + [As an Apache WSGI application](#as-an-apache-wsgi-application)
  + [Other options](#other-options)
* [Transcoding](#transcoding)
* [Command line interface](#command-line-interface)
* [Quickstart](#quickstart)
* [Scanner daemon](#scanner-daemon)
* [Upgrading](#upgrading)

## Installation

Supysonic can run as a standalone application (not recommended for a
"production" server) or as a WSGI application (on Apache for instance).
To install it, run:

    $ python setup.py install

### Prerequisites

You'll need these to run Supysonic:

* Python 2.7
* [Flask](http://flask.pocoo.org/) >= 0.9
* [Storm](https://storm.canonical.com/)
* [Python Imaging Library](https://github.com/python-pillow/Pillow)
* [simplejson](https://simplejson.readthedocs.io/en/latest/)
* [requests](http://docs.python-requests.org/)
* [mutagen](https://mutagen.readthedocs.io/en/latest/)
* [watchdog](https://github.com/gorakhargosh/watchdog)

On a Debian-like OS (Debian, Ubuntu, Linux Mint, etc.), you can install them
this way:

    $ apt-get install python-flask python-storm python-imaging python-simplesjon python-requests python-mutagen python-watchdog

You may also need a database specific package:

* MySQL: `apt install python-mysqldb`
* PostgreSQL: `apt-install python-psycopg2`

Due to a bug in `storm`, `psycopg2` version 2.5 and later does not work
properly. You can either use version 2.4 or [patch storm][storm] yourself.

[storm]: https://bugs.launchpad.net/storm/+bug/1170063

### Configuration

Supysonic looks for two files for its configuration: `/etc/supysonic` and
`~/.supysonic`, merging values from the two files.

Configuration files must respect a structure similar to Windows INI file, with
`[section]` headers and using a `KEY = VALUE` or `KEY: VALUE` syntax.

The sample configuration (`config.sample`) looks like this:

```
[base]
; A Storm database URI. See the 'schema' folder for schema creation scripts
; database_uri = sqlite:////var/supysonic/supysonic.db
; database_uri = mysql://username:password@hostname/database_name
; database_uri = postgres://username:password@hostname/database_name

; Optional, restrict scanner to these extensions
; scanner_extensions = mp3 ogg

[webapp]
; Optional cache directory
cache_dir = /var/supysonic/cache

; Optional rotating log file
log_file = /var/supysonic/supysonic.log

; Log level. Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = WARNING

[daemon]
; Optional rotating log file for the scanner daemon
log_file = /var/supysonic/supysonic-daemon.log
log_level = INFO

[lastfm]
; API and secret key to enable scrobbling. http://www.last.fm/api/accounts
; api_key =
; secret =

[transcoding]
; Programs used to convert from one format/bitrate to another.
transcoder_mp3_mp3 = lame --quiet --mp3input -b %outrate %srcpath -
transcoder = ffmpeg -i %srcpath -ab %outratek -v 0 -f %outfmt -
decoder_mp3 = mpg123 --quiet -w - %srcpath
decoder_ogg = oggdec -o %srcpath
decoder_flac = flac -d -c -s %srcpath
encoder_mp3 = lame --quiet -b %outrate - -
encoder_ogg = oggenc2 -q -M %outrate -

[mimetypes]
; extension to mimetype mappings in case your system has some trouble guessing
; mp3 = audio/mpeg
; ogg = audio/vorbis
```

Note that using SQLite for large libraries might not be the brightest idea
as it tends to struggle with larger datasets.

For mime types, see the [list of common types][types].

[types]: https://en.wikipedia.org/wiki/Internet_media_type#List_of_common_media_types

### Database initialization

Supysonic does not issue the `CREATE TABLE` commands for the tables it needs.
Thus the database and tables must be created prior to running the application.
Table creation scripts are provided in the `schema` folder for SQLite, MySQL
and PostgreSQL.

## Running the application

### As a standalone debug server

It is possible to run Supysonic as a standalone server, but it is only
recommended to do so if you are hacking on the source. A standalone won't
be able to serve more than one request at a time.

To start the server, just run the `cgi-bin/server.py` script.

    $ python cgi-bin/server.py

By default, it will listen on the loopback interface (`127.0.0.1`) on port
5000, but you can specify another address on the command line, for instance
on all the IPv6 interfaces:

    $ python cgi-bin/server.py ::

### As an Apache WSGI application

Supysonic can run as a WSGI application with the `cgi-bin/supysonic.wsgi` file.
To run it within an Apache2 server, first you need to install the WSGI module
and enable it.

    $ apt-get install libapache2-mod-wsgi
    $ a2enmod wsgi

Next, edit the Apache configuration to load the application. Here's a basic
example of what it looks like:

    WSGIScriptAlias /supysonic /path/to/supysonic/cgi-bin/supysonic.wsgi
    <Directory /path/to/supysonic/cgi-bin>
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Order deny,allow
        Allow from all
    </Directory>

You might also need to run Apache using the system default locale, as the one
it uses might cause problems while scanning the library. To do so, edit the
`/etc/apache2/envvars` file, comment the line `export LANG=C` and uncomment
the `. /etc/default/locale` line. Then you can restart Apache:

    $ service apache2 restart

With that kind of configuration, the server address will look like *http://server/supysonic/*

### Other options

If you use another HTTP server, such as *nginx* or *lighttpd*, or prefer to
use FastCGI or CGI over WSGI, FastCGI and CGI scripts are also provided in the
`cgi-bin` folder, respectively as `supysonic.fcgi` and `supysonic.cgi`. As with
WSGI, you might need to edit those file to suit your system configuration.

Here are some quick docs on how to configure your server for [FastCGI][] or [CGI][].

[fastcgi]: http://flask.pocoo.org/docs/deploying/fastcgi/
[cgi]: http://flask.pocoo.org/docs/deploying/cgi/

## Transcoding

Transcoding is the process of converting from one audio format to another. This
allows for streaming of formats that wouldn't be streamable otherwise, or
reducing the quality of an audio file to allow a decent streaming for clients
with limited bandwidth, such as the ones running on a mobile connection.

Supysonic's transcoding is achieved through the use of third-party command-line
programs. Supysonic isn't bundled with such programs, and you are left to
choose which one you want to use.

If you want to use transcoding but your client doesn't allow you to do so, you
can force Supysonic to transcode for that client by going on the web interface.

### Configuration

Configuration of transcoders is done on the `[transcoding]` section of the
configuration file.

Transcoding can be done by one single program which is able to convert from one
format direclty to another one, or by two programs: a decoder and an encoder.
All these are defined by the following variables:

* *transcoder_EXT_EXT*
* *decoder_EXT*
* *encoder_EXT*
* *trancoder*
* *decoder*
* *encoder*

where *EXT* is the lowercase file extension of the matching audio format.
*transcoder*s variables have two extensions: the first one is the source
extension, and the second one is the extension to convert to. The same way,
*decoder*s extension is the source extension, and *encoder*s extension is
the extension to convert to.

Notice that all of them have a version without extension. Those are generic
versions. The programs defined with these variables should be able to
transcode/decode/encode any format. For that reason, we suggest you
don't use these if you want to keep control over the available transcoders.

Supysonic will take the first available transcoding configuration in the
following order:

1. specific transcoder
2. specific decoder / specific encoder
3. generic decoder / generic encoder (with the possibility to use a generic
   decoder with a specific encoder, and vice-versa)
4. generic transcoder

All the variables should be set to the command-line used to run the converter
program. The command-lines can include the following fields:

* `%srcpath`: path to the original file to transcode
* `%srcfmt`: extension of the original file
* `%outfmt`: extension of the resulting file
* `%outrate`: bitrate of the resulting file

One final note: the original file should be provided as an argument of
transcoders and decoders. All transcoders, decoders and encoders should
write to standard output, and encoders should read from standard input.

### Suggested configuration

Here are some example configuration that you could use. This is provided as-is,
and some configurations haven't been tested.

    transcoder_mp3_mp3 = lame --quiet --mp3input -b %outrate %srcpath -
    transcoder = ffmpeg -i %srcpath -ab %outratek -v 0 -f %outfmt -
    decoder_mp3 = mpg123 --quiet -w - %srcpath
    decoder_ogg = oggdec -o %srcpath
    decoder_flac = flac -d -c -s %srcpath
    encoder_mp3 = lame --quiet -b %outrate - -
    encoder_ogg = oggenc2 -q -M %outrate -

## Command line interface

The command-line interface (or CLI, *cli.py*) is an interface allowing
administration operations without the use of the web interface. It can either
be run in interactive mode (`python cli.py`) or to issue a single command
(`python cli.py <arguments>`).

If ran without arguments, `supsonic-cli` will open an interactive prompt. You
can use the command line tool to do a few things:

```
Usage:
    supysonic-cli [help] (user) (folder)

Display the help message

Arguments:
    user                        Display the help message for the user command
    folder                      Display the help message for the folder command
```

```
Usage:
    supysonic-cli user [add] <user> (-a) (-p <password>) (-e <email>)
    supysonic-cli user [delete] <user>
    supysonic-cli user [changepass] <user> <password>
    supysonic-cli user [list]
    supysonic-cli user [setadmin] (--off) <user>

User management commands

Arguments:
    add                         Add a new user
    delete                      Delete the user
    changepass                  Change the user's password
    list                        List all the users
    setadmin                    Give admin rights to the user

Options:
  -a --admin                    Create the user with admin rights
  -p --password <password>      Specify the user's password
  -e --email <email>            Specify the user's email
  --off                         Revoke the admin rights if present
```

```
Usage:
    supysonic-cli folder [add] <name> <path>
    supysonic-cli folder [delete] <name>
    supysonic-cli folder [list]
    supysonic-cli folder [scan] <name>

Folder management commands

Arguments:
    add                         Add a new folder
    delete                      Delete a folder
    list                        List all the folders
    scan                        Scan a specified folder
```

## Quickstart

To start using Supysonic, you'll first have to specify where your music library
is located and create a user to allow calls to the API.

Let's start by creating a new admin user this way:

    $ supysonic-cli user add spl0k -a -p MyAwesomePassword

To add a new folder to your music library, you can do something like this:

    $ supysonic-cli folder add MyLibrary /home/spl0k/Music

Once you've added a folder, you will need to scan it:

    $ supysonic-cli folder scan MyLibrary

You should now be able to enjoy your music with the client of your choice!

## Scanner daemon

Instead of manually running a scan every time your library changes, you can
run a daemon that will listen to any library change and update the database
accordingly. The daemon is `bin/supysonic-watcher` and can be run as an
*init.d* script.

## Upgrading

Some commits might introduce changes in the database schema. When that's
the case migration scripts will be provided in the `schema/migration`
folder, prefixed by the date of commit that introduced the changes. Those
scripts shouldn't be used when initializing a new database, only when
upgrading from a previous schema.
