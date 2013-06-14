Supysonic
=========

Supysonic is a Python implementation of the [Subsonic](http://www.subsonic.org/) server API.

Current supported features are:
* browsing (by folders or ID3 tags)
* streaming (obviously, the collection scanner only looks for MP3s though)
* random playlists
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
* [SQLAlchemy](http://www.sqlalchemy.org/) (`apt-get install sqlalchemy`)
* Python Imaging Library (`apt-get install python-imaging`)
* simplejson (`apt-get install python-simplejson`)
* [requests](http://docs.python-requests.org/) >= 0.12.1 (`pip install requests`)
* [eyeD3](http://eyed3.nicfit.net/) >= 0.7 (`pip install eyed3`)

### Configuration

Supysonic looks for two files for its configuration: `~/.supysonic` or `/etc/supysonic` (in this order).
Options are set using the `KEY = VALUE` syntax. String values must be quote-enclosed.

Available settings are:
* **DATABASE_URI**: a SQLAlchemy [database URI](http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#database-urls).
  I personnaly use SQLite (`sqlite:////var/supysonic/supysonic.db`), but it might not be the brightest
  idea for large libraries.
* **CACHE_DIR**: path to a cache folder. Mostly used for resized cover art images.
* **LOG_FILE**: path and base name of a rolling log file.
* **LASTFM_KEY**: Last.FM [API key](http://www.last.fm/api/accounts) to enable scrobbling
* **LASTFM_SECRET**: Last.FM API secret matching the key.

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
	service apache2 reload

Next, edit the Apache configuration to load the application. Here's a basic example of what it looks like:

	WSGIScriptAlias /supysonic /path/to/supysonic/main.wsgi
	<Directory /path/to/supysonic>
		WSGIApplicationGroup %{GLOBAL}
		Order deny,allow
		Allow from all
	</Directory>

With that kind of configuration, the server address will look like *http://server/supysonic/*

Quickstart
----------

The first time you run the server, open its URL to set the initial configuration. You'll be asked to create
a first user. This user will be an admin of the server.

Once the first user created, log in to the app. Then you can add other users or manage folders. Folders are
where your music is located. Add one, then hit the scan button. The scanning process might take some time on
large libraries, so be patient. Your browser might even timeout even if the process is still running. Once
scanning is done, you can enjoy your music with the client of your choice.

