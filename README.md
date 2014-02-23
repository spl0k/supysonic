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
* [Flask](http://flask.pocoo.org/) >= 0.7 (`pip install flask`)
* [SQLAlchemy](http://www.sqlalchemy.org/) (`apt-get install python-sqlalchemy`)
* Python Imaging Library (`apt-get install python-imaging`)
* simplejson (`apt-get install python-simplejson`)
* [requests](http://docs.python-requests.org/) >= 0.12.1 (`pip install requests`)
* [mutagen](https://code.google.com/p/mutagen/) (`apt-get install python-mutagen`)

### Configuration

Supysonic looks for two files for its configuration: `/etc/supysonic` and `~/.supysonic`, merging values from the two files.
Configuration files must respect a structure similar to Windows INI file, with `[section]` headers and using a `KEY = VALUE`
or `KEY: VALUE` syntax.

Available settings are:
* Section **base**:
  * **database_uri**: required, a SQLAlchemy [database URI](http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#database-urls).
    I personally use SQLite (`sqlite:////var/supysonic/supysonic.db`), but it might not be the brightest idea for large libraries.
  * **cache_dir**: path to a cache folder. Mostly used for resized cover art images. Defaults to `<system temp dir>/supysonic`.
  * **log_file**: path and base name of a rolling log file.
  * **scanner_extensions**: space-separated list of file extensions the scanner is restricted to. If omitted, files will be scanned
    regardless of their extension
* Section **lastfm**:
  * **api_key**: Last.FM [API key](http://www.last.fm/api/accounts) to enable scrobbling
  * **secret**: Last.FM API secret matching the key.
* Section **transcoding**: see [Transcoding](https://github.com/spl0k/supysonic/wiki/Transcoding)
* Section **mimetypes**: extension to content-type mappings. Designed to help the system guess types, to help clients relying on
  the content-type. See [the list of common types](https://en.wikipedia.org/wiki/Internet_media_type#List_of_common_media_types).

### Running as a standalone server

It is possible to run Supysonic as a standalone server, but it is only recommended to do so if you are
hacking on the source. A standalone won't be able to serve more than one request at a time.

To start the server, just run the `main.py` script.

	python main.py

The server will then be available at *http://server:5000/*

### Running as a WSGI application

Supysonic can run as a WSGI application with the `main.wsgi` file. But first you need to edit this
file at line 4 to set the path to the Supysonic app folder.

To run it within an Apache2 server, first you need to install the WSGI module and enable it.

	apt-get install libapache2-mod-wsgi
	a2enmod wsgi

Next, edit the Apache configuration to load the application. Here's a basic example of what it looks like:

	WSGIScriptAlias /supysonic /path/to/supysonic/main.wsgi
	<Directory /path/to/supysonic>
		WSGIApplicationGroup %{GLOBAL}
		Order deny,allow
		Allow from all
	</Directory>

You might also need to run Apache using the system default locale, as the one it uses might cause problems while
scanning the library. To do so, edit the `/etc/apache2/envvars` file, comment the line `export LANG=C` and
uncomment the `. /etc/default/locale` line. Then you can restart Apache.

	service apache2 restart

With that kind of configuration, the server address will look like *http://server/supysonic/*

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

