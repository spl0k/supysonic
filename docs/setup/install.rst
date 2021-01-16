Installing Supysonic
====================

Supysonic is written in Python and supports Python 3.5+.

Linux
-----

Currently, only Debian-based distributions might provide Supysonic in their
package repositories. Install the package ``supysonic`` using :command:`apt`::

   $ apt install supysonic

This will install Supysonic along with the minimal dependencies it needs to
run.

.. note::

   As of January 2021, Supysonic only reached Debian's *testing* release. If
   you're using the *stable* release it might not be available in the packages
   yet.

If you plan on using it with a MySQL or PostgreSQL database you also need the
corresponding Python package, ``python-pymysql`` for MySQL or
``python-psycopg2`` for PostgreSQL.

::

   $ apt install python-pymysql

::

   $ apt install python-psycopg2

For other distributions, you might consider installing from `docker`_ images or
from `source`_.

Windows
-------

.. note::
   While Supysonic hasn't been thoroughly tested on Windows, it *should* work.
   If something is broken, we're really sorry. Don't hesitate to `open an
   issue`__ on GitHub.

   __ https://github.com/spl0k/supysonic/issues

Most Windows users do not have Python installed by default, so we begin with
the installation of Python itself.  To check if you already have Python
installed, open the *Command Prompt* (:kbd:`Win-R` and type :command:`cmd`).
Once the command prompt is open, type :command:`python --version` and press
Enter.  If Python is installed, you will see the version of Python printed to
the screen.  If you do not have Python installed, refer to the `Hitchhikers
Guide to Python's`__ Python on Windows installation guides. You must install
`Python 3`__.

Once Python is installed, you can install Supysonic using :command:`pip`. Refer
to the `source installation instructions <source_>`_ below for more information.

__ https://docs.python-guide.org/
__ https://docs.python-guide.org/starting/install3/win/

.. _docker:

Docker
------

While we don't provide Docker images for Supysonic, that didn't keep the
community from creating some. Take a look on the `Docker Hub`__ and pick one you
like. For more details on their usage, please refer to the readme of said
images.

__ https://hub.docker.com/search?q=supysonic&type=image

.. _source:

Source
------

You can install Supysonic directly from a clone of the `Git repository`__. This
can be done either by cloning the repo and installing from the local clone, or
simply installing directly via :command:`pip`.

::

   $ git clone https://github.com/spl0k/supysonic.git
   $ cd supysonic
   $ pip install .

::

   $ pip install git+https://github.com/spl0k/supysonic.git

This will install Supysonic along with the minimal dependencies it needs to
run.

If you plan on using it with a MySQL or PostgreSQL database you also need the
corresponding package, ``pymysql`` for MySQL or ``psycopg2-binary`` for
PostgreSQL.

::

   $ pip install pymysql

::

   $ pip install psycopg2-binary

__ https://github.com/spl0k/supysonic
