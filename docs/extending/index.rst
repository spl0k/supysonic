Extending Supysonic
===================

A few parts of Supysonic aren't hard-wired into the application but looked up
from the configuration file. For those, the implementations shipped with
Supysonic have no privilege over yours: a module of your own providing the same
interface is enabled the exact same way, by naming it in the configuration.

This guide documents those extension points, one page each, along with the
parts of Supysonic they all rely on.

.. rubric:: Table of contents

.. toctree::
   :maxdepth: 2

   configuration
   scrobblers
   lyrics
