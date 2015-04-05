Supysonic
=========

Supysonic is a Python implementation of the [Subsonic](http://www.subsonic.org/) server API.

Current supported features are:
* browsing (by folders or tags)
* streaming of various audio file formats
* transcoding
* user or random playlists
* cover arts (`cover.jpg` files in the same folder as music files)
* starred tracks/albums and ratings
* [Last.FM](http://www.last.fm/) scrobbling

For more details, go check the [API implementation status wiki page](https://github.com/spl0k/supysonic/wiki/API-implementation-status).

Installation
------------

Supysonic can run as a standalone application (not recommended for a "production" server)
or as a WSGI application (on Apache for instance). But first:

### Prerequisites

* Python 2.7
* [Flask](http://flask.pocoo.org/) >= 0.9 (`pip install flask`)
* [Storm](https://storm.canonical.com/) (`apt-get install python-storm`)
* Python Imaging Library (`apt-get install python-imaging`)
* simplejson (`apt-get install python-simplejson`)
* [requests](http://docs.python-requests.org/) >= 1.0.0 (`pip install requests`)
* [mutagen](https://code.google.com/p/mutagen/) (`apt-get install python-mutagen`)
* [watchdog](https://github.com/gorakhargosh/watchdog) (`pip install watchdog`)

### Configuration

Supysonic looks for two files for its configuration: `/etc/supysonic` and `~/.supysonic`, merging values from the two files.
Configuration files must respect a structure similar to Windows INI file, with `[section]` headers and using a `KEY = VALUE`
or `KEY: VALUE` syntax.

Available settings are:
* Section **base**:
  * **database_uri**: required, a Storm [database URI](https://storm.canonical.com/Manual#Databases).
    I personally use SQLite (`sqlite:////var/supysonic/supysonic.db`), but it might not be the brightest idea for large libraries.
    Note that to use PostgreSQL you'll need *psycopg2* version 2.4 (not 2.5!) or [patch storm](https://bugs.launchpad.net/storm/+bug/1170063).
  * **scanner_extensions**: space-separated list of file extensions the scanner is restricted to. If omitted, files will be scanned
    regardless of their extension
* Section **webapp**
  * **cache_dir**: path to a cache folder. Mostly used for resized cover art images. Defaults to `<system temp dir>/supysonic`.
  * **log_file**: path and base name of a rolling log file.
  * **log_level**: logging level. Possible values are *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*.
* Section **lastfm**:
  * **api_key**: Last.FM [API key](http://www.last.fm/api/accounts) to enable scrobbling
  * **secret**: Last.FM API secret matching the key.
* Section **transcoding**: see [Transcoding](https://github.com/spl0k/supysonic/wiki/Transcoding)
* Section **mimetypes**: extension to content-type mappings. Designed to help the system guess types, to help clients relying on
  the content-type. See [the list of common types](https://en.wikipedia.org/wiki/Internet_media_type#List_of_common_media_types).
* Section **daemon**
  * **log_file**: path and base name of a rolling log file.
  * **log_level**: logging level. Possible values are *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*.

### Database initialization

Supysonic does not issue the `CREATE TABLE` commands for the tables it needs. Thus the database and tables must be created prior to
running the application. Table creation scripts are provided in the *schema* folder for SQLite, MySQL and PostgreSQL.

Running the application
-----------------------

### As a standalone debug server

It is possible to run Supysonic as a standalone server, but it is only recommended to do so if you are
hacking on the source. A standalone won't be able to serve more than one request at a time.

To start the server, just run the `cgi-bin/server.py` script.

	python cgi-bin/server.py

By default, it will listen on the loopback interface (127.0.0.1) on port 5000, but you can specify another address on
the command line, for instance on all the IPv6 interfaces:

	python cgi-bin/server.py ::

### As an Apache WSGI application

Supysonic can run as a WSGI application with the `cgi-bin/supysonic.wsgi` file.
To run it within an Apache2 server, first you need to install the WSGI module and enable it.

	apt-get install libapache2-mod-wsgi
	a2enmod wsgi

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

	service apache2 restart

With that kind of configuration, the server address will look like *http://server/supysonic/*

### Other options

If you use another HTTP server, such as *nginx* or *lighttpd*, or prefer to use FastCGI or CGI over WSGI,
FastCGI and CGI scripts are also providedin the `cgi-bin` folder, respectively as `supysonic.fcgi` and `supysonic.cgi`.
As with WSGI, you might need to edit those file to suit your system configuration.

Here are some quick docs on how to configure your server for [FastCGI](http://flask.pocoo.org/docs/deploying/fastcgi/)
or [CGI](http://flask.pocoo.org/docs/deploying/cgi/).

Quickstart
----------

To start using Supysonic, you'll first have to specify where your music library is located and create a user
to allow calls to the API.

Let's start by creating the user. To do so, use the
[command-line interface](https://github.com/spl0k/supysonic/wiki/Command-Line-Interface) (`cli.py`).
For the folder(s) (music library) you can either use the CLI, or go to the web interface if you gave admin
rights to the user. Once the folder is created, don't forget to scan it to build the music database (it might
take a while depending on your library size, so be patient). Once scanning is done, you can enjoy your music
with the client of your choice.

Scanner daemon
--------------

Instead of manually running a scan every time your library changes, you can run a daemon that will
listen to any library change and update the database accordingly. The daemon is `bin/supysonic-watcher`
and can be run as an *init.d* script.

