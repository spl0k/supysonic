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
[api]: #current-target-api-version

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
  + [Examples](#examples)
* [Quickstart](#quickstart)
* [Scanner daemon](#scanner-daemon)
* [Upgrading](#upgrading)
* [Current target API version](#current-target-api-version)

## Installation

Supysonic can run as a standalone application (not recommended for a "production" server)
or as a WSGI application (on Apache for instance). To install it, run:

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

You may also need a database specific package. For example, if you choose to
use MySQL, you will need to install `python-mysqldb`.

### Configuration

Supysonic looks for two files for its configuration: `/etc/supysonic` and `~/.supysonic`, merging values from the two files.
Configuration files must respect a structure similar to Windows INI file, with `[section]` headers and using a `KEY = VALUE`
or `KEY: VALUE` syntax.

Available settings are:
* Section **base**:
  * **database_uri**: required, a Storm [database URI][].
    I personally use SQLite (`sqlite:////var/supysonic/supysonic.db`), but it might not be the brightest idea for large libraries.
    Note that to use PostgreSQL you'll need *psycopg2* version 2.4 (not 2.5!) or [patch storm](https://bugs.launchpad.net/storm/+bug/1170063).
  * **scanner_extensions**: space-separated list of file extensions the scanner is restricted to. If omitted, files will be scanned
    regardless of their extension
* Section **webapp**
  * **cache_dir**: path to a cache folder. Mostly used for resized cover art images. Defaults to `<system temp dir>/supysonic`.
  * **log_file**: path and base name of a rolling log file.
  * **log_level**: logging level. Possible values are *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*.
* Section **lastfm**:
  * **api_key**: Last.FM [API key][api-key] to enable scrobbling
  * **secret**: Last.FM API secret matching the key.
* Section **transcoding**: see [Transcoding][]
* Section **mimetypes**: extension to content-type mappings. Designed to help the system guess types, to help clients relying on
  the content-type. See [the list of common types][].
* Section **daemon**
  * **log_file**: path and base name of a rolling log file.
  * **log_level**: logging level. Possible values are *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*.

[database-uri]: https://storm.canonical.com/Manual#Databases
[api-key]: http://www.last.fm/api/accounts
[transcoding]: #transcoding
[list-of-the-common-types]: https://en.wikipedia.org/wiki/Internet_media_type#List_of_common_media_types

### Database initialization

Supysonic does not issue the `CREATE TABLE` commands for the tables it needs. Thus the database and tables must be created prior to
running the application. Table creation scripts are provided in the *schema* folder for SQLite, MySQL and PostgreSQL.

## Running the application

### As a standalone debug server

It is possible to run Supysonic as a standalone server, but it is only recommended to do so if you are
hacking on the source. A standalone won't be able to serve more than one request at a time.

To start the server, just run the `cgi-bin/server.py` script.

    $ python cgi-bin/server.py

By default, it will listen on the loopback interface (127.0.0.1) on port 5000, but you can specify another address on
the command line, for instance on all the IPv6 interfaces:

    $ python cgi-bin/server.py ::

### As an Apache WSGI application

Supysonic can run as a WSGI application with the `cgi-bin/supysonic.wsgi` file.
To run it within an Apache2 server, first you need to install the WSGI module and enable it.

    $ apt-get install libapache2-mod-wsgi
    $ a2enmod wsgi

Next, edit the Apache configuration to load the application. Here's a basic example of what it looks like:

    WSGIScriptAlias /supysonic /path/to/supysonic/cgi-bin/supysonic.wsgi
    <Directory /path/to/supysonic/cgi-bin>
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Order deny,allow
        Allow from all
    </Directory>

You might also need to run Apache using the system default locale, as the one it uses might cause problems while
scanning the library. To do so, edit the `/etc/apache2/envvars` file, comment the line `export LANG=C` and
uncomment the `. /etc/default/locale` line. Then you can restart Apache.

    $ service apache2 restart

With that kind of configuration, the server address will look like *http://server/supysonic/*

### Other options

If you use another HTTP server, such as *nginx* or *lighttpd*, or prefer to use FastCGI or CGI over WSGI,
FastCGI and CGI scripts are also providedin the `cgi-bin` folder, respectively as `supysonic.fcgi` and `supysonic.cgi`.
As with WSGI, you might need to edit those file to suit your system configuration.

Here are some quick docs on how to configure your server for [FastCGI][] or [CGI][].

[fastcgi]: http://flask.pocoo.org/docs/deploying/fastcgi/
[cgi]: http://flask.pocoo.org/docs/deploying/cgi/

## Trancoding

Transcoding is the process of converting from one audio format to another. This
allows for streaming of formats that wouldn't be streamable otherwise, or
reducing the quality of an audio file to allow a decent streaming for clients
with limited bandwidth, such as the ones running on a mobile connection.

Supysonic's transcoding is achieved through the use of third-party command-line
programs. Supysonic isn't bundled with such programs, and you are left to
choose which one you want to use.

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

Supysonic will take the first available transcoding configuration in the following order:

1. specific transcoder
2. specific decoder / specific encoder
3. generic decoder / generic encoder (with the possibility to use a generic decoder with a specific encoder, and vice-versa)
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
    user                        Display the help mesage for the user command
    folder                      Display the help mesage for the folder command
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

### Examples

You can add a new admin user this way:

    $ supysonic-cli user add spl0k -a -p MyAwesomePassword

To add a new folder, you can use something like this:

    $ supysonic-cli folder add MyLibrary /home/spl0k/Music

Once you've added it, you will need to scan it:

    $ supysonic-cli folder scan MyLibrary
    
## Quickstart

To start using Supysonic, you'll first have to specify where your music library is located and create a user
to allow calls to the API.

Let's start by creating the user. To do so, use the [command-line interface][] (`cli.py`).
For the folder(s) (music library) you can either use the CLI, or go to the web interface if you gave admin
rights to the user. Once the folder is created, don't forget to scan it to build the music database (it might
take a while depending on your library size, so be patient). Once scanning is done, you can enjoy your music
with the client of your choice.

[command-line-interface]: #command-line-interface

## Scanner daemon

Instead of manually running a scan every time your library changes, you can run a daemon that will
listen to any library change and update the database accordingly. The daemon is `bin/supysonic-watcher`
and can be run as an *init.d* script.

## Upgrading

Some commits might introduce changes in the database schema. When that's the case migration scripts will
be provided in the *schema/migration* folder, prefixed by the date of commit that introduced the changes.
Those scripts shouldn't be used when initializing a new database, only when upgrading from a previous schema.

## Current target API version

At the moment, the current target API version is 1.8.0

<table>
  <tr><th>Module</th><th>API call</th><th>Status</th><th>Comments</th></tr>

  <tr><th rowspan="2">System</th>	<td>ping</td>	<td style="background-color: green">Done</td>	<td></td></tr>
  <tr>	<td>getLicense</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="9">Browsing</th>	<td>getMusicFolders</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getIndexes</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getMusicDirectory</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getGenres</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>getArtists</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getArtist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getAlbum</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getSong</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getVideos</td>	<td>Done</td>	<td>Actually returns an error as video support is not planned</td></tr>

  <tr><th rowspan="7">Album/song lists</th>	<td>getAlbumList</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getAlbumList2</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getRandomSongs</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getSongsByGenre</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>getNowPlaying</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getStarred</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getStarred2</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="3">Searching</th>	<td>search</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>search2</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>search3</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="5">Playlists</th>	<td>getPlaylists</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getPlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>createPlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>updatePlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>deletePlaylist</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="6">Media retrieval</th>	<td>stream</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>download</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>hls</td>	<td>N/A</td>	<td>Video related stuff, not planned</td></tr>
  <tr>	<td>getCoverArt</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getLyrics</td>	<td>Done</td>	<td>Use either text files or ChartLyrics API</td></tr>
  <tr>	<td>getAvatar</td>	<td><strong>TODO</strong></td>	<td>Not that useful for a streaming server, but whatever</td></tr>

  <tr><th rowspan="4">Media annotation</th>	<td>star</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>unstar</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>setRating</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>scrobble</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="4">Sharing</th>	<td>getShares</td>	<td><strong>TODO</strong></td>	<td rowspan="4">Need to look how this works on the official Subsonic server</td></tr>
  <tr>	<td>createShare</td>	<td><strong>TODO</strong></td></tr>
  <tr>	<td>updateShare</td>	<td><strong>TODO</strong></td></tr>
  <tr>	<td>deleteShare</td>	<td><strong>TODO</strong></td></tr>

  <tr><th rowspan="6">Podcast</th>	<td>getPodcasts</td>	<td>N/A</td>	<td>Not planning to support podcasts at the moment</td></tr>
  <tr>	<td>refreshPodcasts</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>createPodcastChannel</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deletePodcastChannel</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deletePodcastEpisode</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>downloadPodcastEpisode</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>

  <tr><th>Jukebox</th>	<td>jukeboxControl</td>	<td>N/A</td>	<td>Not planning to support the Jukebox feature</td></tr>

  <tr><th>Internet radio</th>	<td>getInternetRadioStations </td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>

  <tr><th rowspan="2">Chat</th>	<td>getChatMessages</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>addChatMessage </td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="5">User management</th>	<td>getUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getUsers</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>createUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>deleteUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>changePassword </td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="3">Bookmarks</th>	<td>getBookmarks</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>createBookmark</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deleteBookmark</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
</table>
