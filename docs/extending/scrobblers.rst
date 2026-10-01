Scrobblers
==========

A *scrobbler* is a service playback gets reported to. Supysonic ships with two
of them, `Last.fm`__ and `ListenBrainz`__, but neither is special: both are
loaded because they're named in the :ref:`conf-webapp` ``scrobblers`` option,
and anything else named there is loaded the same way.

__ https://www.last.fm/
__ https://listenbrainz.org/

A scrobbler is self-contained. It owns its section of the configuration file,
the tables holding whatever it needs to remember, the routes letting a user
link and unlink their account, and the fragment displaying its status on the
user profile page. Nothing outside of it knows it exists, and a scrobbler
needing none of that gets away with implementing three methods.

Loading
-------

.. highlight:: ini

Scrobblers are loaded from the ``scrobblers`` option of the :ref:`conf-webapp`,
a space-separated list::

   [webapp]
   scrobblers = lastfm myplugins.logscrobbler

A bare name is one of the scrobblers provided by Supysonic. A name holding a dot
is the path of a Python module to import as-is, which must be importable from
the process running the web application. Note that this means a top-level module
can't be used directly: put it in a package, so it has a dotted path.

The module must hold a ``SCROBBLER`` attribute naming its ``Scrobbler``
subclass. Anything else — a module that can't be imported, one without that
attribute, or an attribute that isn't a ``Scrobbler`` subclass — aborts the
startup with a ``ScrobblerImportError`` naming the offending configuration
value.

Each loaded scrobbler is then built with the whole configuration, and asked
whether it's :attr:`~supysonic.scrobblers.Scrobbler.configured`. One that says
no is dropped: it gets no routes and no section on the profile page, as if it
hadn't been listed at all, and a warning in the log says so. The rest of the
application may therefore assume that a loaded scrobbler is usable.

The ``Scrobbler`` interface
---------------------------

.. autoclass:: supysonic.scrobblers.Scrobbler
   :members:
   :special-members: __init__

   :attr:`blueprint`, :attr:`profile_template` and :attr:`models` are the
   optional ones, each defaulting to nothing: see :ref:`scrobbler-views` and
   :ref:`scrobbler-tables` below for what declaring them buys. The rest has to
   be implemented.

   The configuration handed to :meth:`__init__` is the whole of it, out of
   which the scrobbler reads its own section — see :doc:`configuration`.

.. _scrobbler-errors:

Errors
------

.. automodule:: supysonic.scrobblers.exceptions
   :members:
   :member-order: bysource

Only ``ScrobblerImportError`` is raised by Supysonic. The other two are there
for a scrobbler to raise as it links an account, so that its own view can catch
``ScrobblerError`` and show the message to the user rather than telling the two
failures apart. Reusing them isn't mandatory, but a message worth reading is,
since it's shown to the user as-is.

.. _scrobbler-tables:

Persisting state
----------------

A scrobbler remembering something, such as a per-user authentication token,
does so in its own tables, declared as `peewee models`__ on
``supysonic.db.proxy.Model``. Listing them in ``models`` is enough for the
tables to be created at startup if they're missing.

__ https://docs.peewee-orm.com/en/latest/peewee/models.html

.. note::

   There is no migration mechanism for those tables. If you're a scrobbler
   author and need to change its database schema, `file an issue`__ so
   migrations can be considered.

__ https://github.com/spl0k/supysonic/issues

.. _scrobbler-views:

Routes and the profile page
---------------------------

.. highlight:: python

Linking an account is done from the user profile page, which means a scrobbler
needing one provides both a fragment of that page and the routes its fragment
submits to.

The routes live on a Flask blueprint, built at import time — not once the
scrobbler is instantiated — with ``make_blueprint``::

   from supysonic.scrobblers import make_blueprint

   blueprint = make_blueprint("myscrobbler", __name__)

This mounts it under ``/scrobbler/myscrobbler/`` and, more importantly,
installs the frontend's login check on it, so none of its routes can be left
unauthenticated by accident.

Views are then declared on it as on any blueprint. A view acting on a user
should take a ``uid`` and be decorated with ``me_or_uuid``, which resolves it
to the matching user and hands it over as a second argument. ``me`` is the
logged-in user; any other id is reserved to admins::

   from flask import flash, redirect, url_for

   from supysonic.app.flask import app_layer
   from supysonic.frontend._helpers import me_or_uuid
   from supysonic.scrobblers.exceptions import ScrobblerError


   @blueprint.post("/<uid>/link")
   @me_or_uuid
   def link(uid, user):
       try:
           app_layer.get_scrobbler("myscrobbler").link_account(user, "the token")
       except ScrobblerError as e:
           flash(str(e), "danger")
       else:
           flash("Successfully linked account", "success")

       return redirect(url_for("frontend.user_profile", uid=uid))

``app_layer.get_scrobbler(name)`` is how a view reaches its own instance: the
blueprint is a module-level object shared by every application, while the
scrobbler is built per application.

The fragment itself goes in a ``templates`` directory next to the module
declaring the blueprint, and its name is what ``profile_template`` holds.
Templates are a flat namespace shared by every blueprint, so naming it after
the scrobbler is what keeps it from colliding with another one's.

It is rendered with the profile page's own context, of which three names
matter: ``user``, the user whose profile is displayed, ``request.user``, the
one looking at it, and ``scrobbler``, the instance. Anything else it needs is
up to the scrobbler to expose — the shipped ones add a ``link(user)`` method
returning the user's link row, or ``None``.

.. highlight:: html+jinja

::

   {%- set uid = 'me' if request.user.id == user.id else user.id -%}
   <form method="post" action="{{ url_for('myscrobbler.link', uid = uid) }}">
     <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
     ...
   </form>

Note the CSRF token: the protection applies to scrobbler blueprints as it does
to the rest of the web interface, so any form submitted with ``POST`` needs it.

A simple example
----------------

Here's a scrobbler doing nothing but writing played tracks to the log. It has
no account to link and nothing to remember, which means no routes, no fragment
and no models — the whole thing is one class.

It lives in a package, so that it has a dotted path to list in the
configuration file::

   myplugins/
       __init__.py
       logscrobbler.py

.. highlight:: python

``myplugins/logscrobbler.py``::

   import logging

   from supysonic.config import Option, Section
   from supysonic.scrobblers import Scrobbler

   logger = logging.getLogger(__name__)


   class LogScrobblerSection(Section, section="logscrobbler"):
       log_level = Option("INFO")


   class LogScrobbler(Scrobbler):
       name = "logscrobbler"

       def __init__(self, config):
           section = config.section(LogScrobblerSection)
           self.__level = logging.getLevelName(section.log_level)

       @property
       def configured(self):
           # getLevelName hands back a 'Level FOO' string for a name it doesn't
           # know, so an unusable log level keeps this scrobbler from loading
           return isinstance(self.__level, int)

       def is_linked(self, user):
           return True  # Everyone is reported, no linking needed

       def now_playing(self, user, track, client):
           logger.log(
               self.__level, "%s is playing %s on %s", user.name, track.title, client
           )

       def scrobble(self, user, track, ts, client):
           logger.log(
               self.__level, "%s played %s on %s", user.name, track.title, client
           )


   SCROBBLER = LogScrobbler

.. highlight:: ini

And the configuration enabling it, alongside the scrobblers shipped with
Supysonic::

   [webapp]
   scrobblers = lastfm listenbrainz myplugins.logscrobbler

   [logscrobbler]
   log_level = DEBUG
