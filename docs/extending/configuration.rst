Configuration
=============

Anything needing to be configured doesn't get a dictionary of whatever was under
its name in the configuration file: it declares the options it takes, and reads
them back off the configuration it's handed. The mechanism is the same one the
core sections use, so an option provided by an extension behaves exactly like
one built into Supysonic.

The configuration file itself, and the sections Supysonic ships with, are
documented in the :doc:`configuration guide <../setup/configuration>`.

Declaring a section
-------------------

A section is a subclass of ``supysonic.config.Section``, naming the section of
the configuration file it reads with the ``section`` class keyword, and
declaring each of its values as an ``Option``.

.. highlight:: python

::

   from functools import partial

   from supysonic.config import Option, Section
   from supysonic.parsers import parse_bool, parse_int


   class MyConfigSection(Section, section="myconfig"):
       api_url = Option("https://example.org/api")
       api_key = Option()
       timeout = Option(5, partial(parse_int, min=1))
       verbose = Option(False, parse_bool)

Which reads the following:

.. highlight:: ini

::

   [myconfig]
   api_key = 0123456789abcdef
   timeout = 30

An ``Option`` takes the default to use when the key isn't in the file, and
optionally a parser turning the string read from it into something else. Without
a parser the value is used as it was read, as a string. The default is *not*
passed through the parser, so it should already be of the type the consumer
expects — ``Option(5, ...)`` above, not ``Option("5", ...)``.

The parsers Supysonic uses itself live in ``supysonic.parsers``: ``parse_bool``,
``parse_int``, ``parse_float``, ``parse_words`` and a few more. Those taking
bounds are bound with ``functools.partial``, as ``timeout`` does above. A parser
is otherwise just a callable taking the string and returning the value, so any
function of yours does, as long as it raises ``ValueError`` on a value it can't
make sense of. That exception is caught and re-raised naming the section and the
option, giving the user something actionable rather than a traceback.

Options can also be shared between sections by declaring them on a mixin, which
is how Supysonic gives the same logging options to its web application and to
its daemon. Options are collected across the whole class hierarchy, so a mixin
holding nothing but ``Option`` attributes is enough.

.. autoclass:: supysonic.config.Option

.. autoclass:: supysonic.config.Section

Reading a section
-----------------

An extension is handed the whole ``Config``, out of which it takes its own
section:

.. highlight:: python

::

   section = config.section(MyConfigSection)
   print(section.api_url, section.timeout)

.. automethod:: supysonic.config.Config.section

Values are plain attributes of the returned object. There's no dictionary
access and no ``get()``: an option that wasn't declared can't be read, and a
declared one always has a value, be it the default or ``None``.

The section is built the first time it's asked for and cached afterwards, so
reading it twice gives the same instance. That also means this is when the
values are parsed, and when an invalid one is reported: doing it as the
extension is built, rather than the first time the value is used, is what keeps
a typo in the configuration file from surfacing later.

A few things worth knowing
--------------------------

* Sections are read-only. Building one is the only way to give it values, which
  makes a configuration something that can be passed around without being
  defended.
* Keys no ``Option`` declares are silently ignored, so an extension can't
  stumble on a key it doesn't know about.
* Sections Supysonic doesn't know about are kept as they're read. This is what
  lets an extension have a section of the configuration file to itself: no
  matter that nothing in the core declares ``[myconfig]``, its contents are
  still there when the extension asks for them.
* A section whose keys are all user-provided, and which therefore can't declare
  options at all, is declared as a :class:`~supysonic.config.MappingSection`
  instead. It's a read-only ``Mapping`` over the raw contents of the section.
  Supysonic uses it for the ``[mimetypes]`` section.

.. autoclass:: supysonic.config.MappingSection
