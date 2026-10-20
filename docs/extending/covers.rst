Cover art providers
===================

A *cover art provider* is a source of the images that clients, the music players
connecting to Supysonic, show next to folders, artists, albums and songs. Each
one listed in the :ref:`conf-webapp` ``cover_art_providers`` option is
consulted, and the images they have are the ones clients get.

Even the images found in the library come from providers: ``folder`` serves the
image files lying next to the tracks, as picked by the scanner, and ``embedded``
the images stored in the tags of the track files. Both are listed by default.
Like any other, they can be reordered, left out, or listed alongside providers
of your own.

Like :doc:`lyrics providers <lyrics>`, a cover art provider has nothing to do
with users: it has no routes, no fragment on the profile page and no tables.

Loading
-------

.. highlight:: ini

Providers are loaded from the ``cover_art_providers`` option of the
:ref:`conf-webapp`, a space-separated list::

   [webapp]
   cover_art_providers = folder embedded myplugins.albumartdir

A bare name is one of the providers shipped with Supysonic. A name holding a dot
is the path of a Python module to import as-is, which must be importable from
the process running the web application. Note that this means a top-level
module can't be used directly: put it in a package, so it has a dotted path.

The module must hold a ``PROVIDER`` attribute naming its ``CoverArtProvider``
subclass. Anything else — a module that can't be imported, one without that
attribute, or an attribute that isn't a ``CoverArtProvider`` subclass — aborts
the startup with a ``CoverArtProviderImportError`` naming the offending
configuration value.

Each loaded provider is then built with the whole configuration, and asked
whether it's :attr:`~supysonic.covers.CoverArtProvider.configured`. One that
says no is dropped, as if it hadn't been listed at all, and a warning in the
log says so. The rest of the application may therefore assume that a loaded
provider is usable.

Announcing and serving
----------------------

Clients browse a library in two ways. By folder, following the directories the
music files are stored in, or by tags, going from an artist to its albums and
from an album to its songs, whatever the directories. Supysonic keeps both
views, as :class:`~supysonic.db.models.Folder` objects for the former, and
:class:`~supysonic.db.models.Artist`, :class:`~supysonic.db.models.Album` and
:class:`~supysonic.db.models.Track` objects for the latter. These are the
*entities* a provider deals with. A track belongs to both views: it lies in a
folder and is part of an album.

A client gets an image in two steps:

#. Whenever Supysonic sends it a list of entities, such as the contents of a
   folder or the albums of an artist, each entity comes with an *image id*, or
   without one if it has no image.
#. To show an image, the client then asks Supysonic for it by that id,
   possibly at a given size.

A client never asks for "the cover of this album", only for an image id it was
given. A provider therefore takes part in both steps.

When entities are listed, :meth:`~supysonic.covers.CoverArtProvider.find_covers`
tells which of them it has an image for, and the image id to send along with
each. An entity no provider has anything for is sent without an image id, so
clients don't ask for images that don't exist.

When a client then asks for an image,
:meth:`~supysonic.covers.CoverArtProvider.get_cover` is given the entity the
image id names, and hands the image over. Providers are asked in the order
they're listed, until one of them has it. Resizing the image to the size the
client asked for, caching the result and telling the image format are
Supysonic's business, not the provider's.

Own covers and fallbacks
~~~~~~~~~~~~~~~~~~~~~~~~

An image belongs to a single entity: the image file of a folder belongs to that
folder, the image embedded in a track to that track. That's the only entity
:meth:`~supysonic.covers.CoverArtProvider.get_cover` answers for.

Other entities may still show it, by falling back on it: a track without an
image of its own shows the one of its folder. This is done by
:meth:`~supysonic.covers.CoverArtProvider.find_covers`, announcing the id of
the entity the image belongs to rather than the id of the entity it was asked
about. With the providers shipped with Supysonic:

=========  ===================================  ========================================
Entity     ``folder`` announces                 ``embedded`` announces
=========  ===================================  ========================================
Folder     its own id, if it has an image file  a track of it having an embedded image
Artist     nothing                              nothing
Album      the folder of one of its tracks      one of its tracks
Track      its folder                           its own id, if it has an embedded image
=========  ===================================  ========================================

When several providers have something for the same entity, its own cover is
preferred over a fallback one, whatever the order they're listed in. Only
between two own covers, or two fallbacks, does the order decide. So a track
with an embedded image shows it rather than the image of its folder, even
though ``folder`` comes first, while an album shows the image file of its
folder rather than the image embedded in one of its tracks.

Whatever image id a provider announces, it has to be served: ``get_cover`` must
then answer for the entity that id names. Only announced ids lead to an image:
a client asking for an image only ever gets the own cover of the entity the id
names, Supysonic never looks for a fallback by itself.

Cost
~~~~

:meth:`~supysonic.covers.CoverArtProvider.find_covers` is called every time
entities are listed to a client, for the whole list at once: a single list may
hold hundreds of songs. It therefore has to be cheap, relying on what's in the
database rather than on files or remote services, and issue a fixed number of
queries whatever the number of entities. The foreign keys of the entities it's
given are already loaded. A provider having nothing for a type of entity
returns an empty ``dict`` without querying anything.

:meth:`~supysonic.covers.CoverArtProvider.get_cover`, called for a single image
a client asked for, may take its time: reading files or querying a remote
service is fine there.

The ``CoverArtProvider`` interface
----------------------------------

.. autoclass:: supysonic.covers.CoverArtProvider
   :members:
   :special-members: __init__

   The configuration handed to :meth:`__init__` is the whole of it, out of
   which the provider reads its own section — see :doc:`configuration`.

.. autoclass:: supysonic.covers.Cover

Errors
------

.. automodule:: supysonic.covers.exceptions
   :members:
   :member-order: bysource

Only ``CoverArtProviderImportError`` is raised, by Supysonic as it loads the
providers. A provider itself never raises: see
:meth:`~supysonic.covers.CoverArtProvider.get_cover`.

A simple example
----------------

Neither provider shipped with Supysonic has covers of its own for albums: they
fall back on those of folders or tracks. Here's one that has, reading them from
a directory of image files, each named after the artist and name of an album.
It lives in a package, so that it has a dotted path to list in the
configuration file::

   myplugins/
       __init__.py
       albumartdir.py

.. highlight:: python

``myplugins/albumartdir.py``::

   import os.path

   from supysonic.config import Option, Section
   from supysonic.covers import Cover, CoverArtProvider
   from supysonic.db.models import Album

   EXTENSIONS = (".jpg", ".jpeg", ".png")


   class AlbumArtDirSection(Section, section="albumartdir"):
       path = Option()


   class AlbumArtDirProvider(CoverArtProvider):
       name = "albumartdir"

       def __init__(self, config):
           self.__path = config.section(AlbumArtDirSection).path

           # Listed once and for all, find_covers() can't afford to look at
           # files. Images added later are only seen after a restart.
           self.__files = {}
           if self.configured:
               for entry in os.scandir(self.__path):
                   stem, ext = os.path.splitext(entry.name)
                   if entry.is_file() and ext.lower() in EXTENSIONS:
                       self.__files[stem.lower()] = entry.path

       @property
       def configured(self):
           return self.__path is not None and os.path.isdir(self.__path)

       def __file(self, album):
           return self.__files.get(f"{album.artist.name} - {album.name}".lower())

       def find_covers(self, entities):
           # Only albums have a cover here, and it's their own
           return {
               a.id: a.id
               for a in entities
               if isinstance(a, Album) and self.__file(a) is not None
           }

       def get_cover(self, entity):
           if not isinstance(entity, Album):
               return None

           path = self.__file(entity)
           if path is None or not os.path.isfile(path):
               return None

           return Cover(path=path)


   PROVIDER = AlbumArtDirProvider

.. highlight:: ini

And the configuration enabling it. Its covers being the own ones of the albums,
they're preferred over the fallbacks of the other providers, even though it's
listed last::

   [webapp]
   cover_art_providers = folder embedded myplugins.albumartdir

   [albumartdir]
   path = /srv/music/covers
