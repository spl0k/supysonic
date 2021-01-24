Using Supysonic
===============

Now that everything is :doc:`set up <setup/index>`, there's actually some more
administrative tasks to perform before really being able to access your music.
The first one being :ref:`usage-users` and next :ref:`usage-folders`. Then you
can choose one of the many :ref:`usage-clients` and you're good to go.

.. _usage-users:

Adding users
------------

One of the first thing you want to do is to create the user(s) that will be
allowed to access Supysonic. The first user has to be created with the
:abbr:`CLI (command-line interface)` (:doc:`manpage here <man/supysonic-cli>`),
if you set them as an admin this new user will then be able to add more users
through :ref:`usage-web`.

Creating a new user and giving them administrative rights is done with the
following two commands::

   $ supysonic-cli user add TheUserName
   $ supysonic-cli user setroles --admin TheUserName

The first command will ask for a password but you can also provide it on the
command-line::

   $ supysonic-cli user add TheUserName --password ThePassword

If you don't want to set the user as an admin but still want them to be able to
use the :doc:`jukebox`, you can give them the right like so::

   $ supysonic-cli user setroles --jukebox TheUserName

This last one isn't needed for admins as they have full control over the
installation.

.. _usage-folders:

Defining and scanning folders
-----------------------------

Supysonic will be pretty useless if you don't tell it where your music is
located. This can once again be done with the CLI or the web interface.

Using the CLI::

   $ supysonic-cli folder add SomeFolderName /path/where/the/music/is

The next step is now to scan the folder to find all the media files it holds::

   $ supysonic-cli folder scan SomeFolderName

If :doc:`setup/daemon` is running, this will start scanning in the background,
otherwise you'll have to wait for the scan to end. This can take some time if
you have a huge library.

.. _usage-web:

The web interface
-----------------

Once you have created a user, you can access the web interface at the root URL
where the application is deployed. As Supysonic is mostly a server and not a
media player this interface won't provide much. It is mainly used for
administrative purposes but also provides some features for regular users that
are only available through this interface.

Once logged, users can click on their username in the top bar to access some
settings. These include the ability to link their Last.fm__ account provided
Supysonic was :ref:`configured <conf-lastfm>` with Last.fm API keys. Once linked
clients will then be able to send *scrobbles*.

.. note::

   In the case of Android clients (this haven't been tested with iOS) this could
   lead to *scrobbles* being sent twice if the official Last.fm application is
   also installed on the device.

Another setting also available only through the web interface is the ability to
define the :ref:`preferred transcoding format <transcoding-enable>`.

Admins got two more options accessible from the top bar: the ability to manage
users and folders. But these have limitations compared to the CLI: you can't
grant or revoke the users' jukebox privilege and you can scan folders you
added only if :doc:`setup/daemon` is running.

__ https://www.last.fm/

.. _usage-clients:

Clients
-------

You'll need a client to access your music. Whether you want an app for your
smartphone, something running on your desktop or in a web page you got several
options here.

One good start would be looking at the list on `Subsonic website`__ but that
list *could* be a bit out of date and there's also some players that don't
appear here. Also disregard the trial notice there, Supysonic doesn't include
such nonsense.

Here are some hand-picked clients:

* in your browser:

  * SubPlayer__ (source__, especially designed to work with Supysonic)
  * Jamstash__ (source__, whose maintainer contributed to Supysonic)

* on Android:

  * Ultrasonic__ (source__, whose maintainer contributed to Supysonic)
  * DSub__ (source__)

* on iOS device:

  * you'll have to find one yourself 😉

* for the desktop (none of them were tested)

  * Clementine__
  * MusicBee__ with a plugin__

.. note::

   The Subsonic API provides several authentication methods. One of them, known
   as *token authentication* was added with API version 1.13.0. As Supysonic
   currently targets API version 1.9.0, the token based method isn't supported.
   So if your client offers you the option, you'll have to disable the token
   based authentication for it to work.

__ http://www.subsonic.org/pages/apps.jsp
__ https://subplayer.netlify.app/
__ https://github.com/peguerosdc/subplayer
__ https://jamstash.com/
__ https://github.com/tsquillario/Jamstash
__ https://play.google.com/store/apps/details?id=org.moire.ultrasonic
__ https://github.com/ultrasonic/ultrasonic/
__ https://play.google.com/store/apps/details?id=github.daneren2005.dsub
__ https://github.com/daneren2005/Subsonic
__ https://www.clementine-player.org
__ https://getmusicbee.com
__ https://getmusicbee.com/addons/plugins/41/subsonic-client/
