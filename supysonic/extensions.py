# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Loading of the extensions named in the configuration file.

Each family of extension (scrobblers, lyrics providers) is a package holding the
implementations shipped with Supysonic, a base class every implementation
derives from, and the name of the module attribute pointing at that
implementation. What's below is shared by all of them.
"""

from importlib import import_module


def load_extension_class(name, *, package, attribute, base, error, kind):
    """Import the extension class configured as ``name``.

    A bare name is one of the extensions shipped in ``package``, anything with a
    dot is the path of a module to import as-is. That module must expose the
    class as ``attribute``, and that class must derive from ``base``.

    :param error: exception class raised when any of the above doesn't hold.
    :param kind: what the extension is, as worded in the error messages.
    """

    module_name = name if "." in name else f"{package}.{name}"

    try:
        module = import_module(module_name)
    except ImportError as e:
        raise error(f"Can't import {kind} {name!r}: {e}") from e

    cls = getattr(module, attribute, None)
    if cls is None:
        raise error(f"Module {module_name!r} defines no {attribute}")

    if not (isinstance(cls, type) and issubclass(cls, base)):
        raise error(f"{attribute} of {module_name!r} isn't a {base.__name__} subclass")

    return cls


def load_extensions(names, config, *, logger, **class_kwargs):
    """Build the extensions listed in ``names``, in that order.

    Each class is looked up with :func:`load_extension_class`, to which
    ``class_kwargs`` are passed, then built with the whole ``config``.

    One that isn't properly configured is left out rather than loaded
    half-working, as if it hadn't been listed at all. Only a warning on
    ``logger`` tells it apart, since being listed says it was meant to work.
    """

    extensions = []
    for name in names:
        cls = load_extension_class(name, **class_kwargs)
        extension = cls(config)
        if not extension.configured:
            logger.warning(
                "%s %r isn't properly configured, it won't be loaded",
                class_kwargs["kind"].capitalize(),
                name,
            )
        else:
            extensions.append(extension)

    return extensions
