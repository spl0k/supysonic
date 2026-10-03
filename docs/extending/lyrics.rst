Lyrics providers
================

A *lyrics provider* is where the ``getLyrics`` API endpoint looks for the lyrics
of a song. Each one listed in the :ref:`conf-webapp` ``lyrics_providers`` option
is asked in turn, in the order they're listed, and the first one finding
anything answers the request. When none does, the client is told there are no
lyrics.

Even reading lyrics off the library is done by providers: ``embedded`` reads
them from the tags of the track files and ``sidecar`` from a text file next to
them, and both are listed by default. Like any other, they can be reordered,
left out, or listed alongside providers of your own.

Contrary to :doc:`scrobblers <scrobblers>`, a provider has nothing to do with
users: lyrics are the same for everyone. It therefore has no routes, no
fragment on the profile page and no tables, and comes down to a single method.

Loading
-------

.. highlight:: ini

Providers are loaded from the ``lyrics_providers`` option of the
:ref:`conf-webapp`, a space-separated list::

   [webapp]
   lyrics_providers = embedded sidecar myplugins.lyricsdir

A bare name is one of the providers shipped with Supysonic. A name holding a dot
is the path of a Python module to import as-is, which must be importable from
the process running the web application. Note that this means a top-level
module can't be used directly: put it in a package, so it has a dotted path.

The module must hold a ``PROVIDER`` attribute naming its ``LyricsProvider``
subclass. Anything else — a module that can't be imported, one without that
attribute, or an attribute that isn't a ``LyricsProvider`` subclass — aborts the
startup with a ``LyricsProviderImportError`` naming the offending configuration
value.

Each loaded provider is then built with the whole configuration, and asked
whether it's :attr:`~supysonic.lyrics.LyricsProvider.configured`. One that says
no is dropped, as if it hadn't been listed at all, and a warning in the log says
so. The rest of the application may therefore assume that a loaded provider is
usable.

The ``LyricsProvider`` interface
--------------------------------

.. autoclass:: supysonic.lyrics.LyricsProvider
   :members:
   :special-members: __init__

   The configuration handed to :meth:`__init__` is the whole of it, out of
   which the provider reads its own section — see :doc:`configuration`.

.. autoclass:: supysonic.lyrics.Lyrics

The artist and title a client sends are whatever its user typed or whatever its
own tags say, so they're best treated as search terms, not identifiers. They're
also untrusted input: a provider building a file path or a URL out of them has
to make sure they can't point anywhere else than intended.

Errors
------

.. automodule:: supysonic.lyrics.exceptions
   :members:
   :member-order: bysource

Only ``LyricsProviderImportError`` is raised, by Supysonic as it loads the
providers. A provider itself never raises: see
:meth:`~supysonic.lyrics.LyricsProvider.get_lyrics`.

A simple example
----------------

Here's a provider reading lyrics from a directory of text files, each named
after the artist and title of a song. It lives in a package, so that it has a
dotted path to list in the configuration file::

   myplugins/
       __init__.py
       lyricsdir.py

.. highlight:: python

``myplugins/lyricsdir.py``::

   import logging
   import os.path

   from supysonic.config import Option, Section
   from supysonic.lyrics import Lyrics, LyricsProvider

   logger = logging.getLogger(__name__)


   class LyricsDirSection(Section, section="lyricsdir"):
       path = Option()


   class LyricsDirProvider(LyricsProvider):
       name = "lyricsdir"

       def __init__(self, config):
           self.__path = config.section(LyricsDirSection).path

       @property
       def configured(self):
           return self.__path is not None and os.path.isdir(self.__path)

       def get_lyrics(self, artist, title):
           filename = f"{artist} - {title}.txt"
           # Both come from the client: don't let them escape the directory
           if os.path.basename(filename) != filename:
               return None

           try:
               with open(os.path.join(self.__path, filename), encoding="utf-8") as f:
                   return Lyrics(artist, title, f.read())
           except FileNotFoundError:
               return None
           except (OSError, UnicodeError) as e:
               logger.warning("Can't read lyrics file %r: %s", filename, e)
               return None


   PROVIDER = LyricsDirProvider

.. highlight:: ini

And the configuration enabling it, after the providers shipped with Supysonic::

   [webapp]
   lyrics_providers = embedded sidecar myplugins.lyricsdir

   [lyricsdir]
   path = /srv/music/lyrics
