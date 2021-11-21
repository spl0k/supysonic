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

If you plan on using it with a MySQL or PostgreSQL database you also need the
corresponding Python package, ``python-pymysql`` for MySQL or
``python-psycopg2`` for PostgreSQL.

::

   $ apt install python-pymysql

::

   $ apt install python-psycopg2

For other distributions, you might consider installing  with `pip`_ or from
:ref:`docker` images.

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
to the `installation instructions <pip_>`_ below for more information.

__ https://docs.python-guide.org/
__ https://docs.python-guide.org/starting/install3/win/

.. _pip:

pip
---

Simply install the package ``supysonic`` with :command:`pip`::

   $ pip install supysonic

This will install Supysonic along with the minimal dependencies it needs, but
those don't include the requirements for the web server. For this you'll need
to install either ``gevent``, ``gunicorn`` or ``waitress``.

::

   $ pip install gevent

::

   $ pip install gunicorn

::

   $ pip install waitress

If you plan on using it with a MySQL or PostgreSQL database you also need the
corresponding package, ``pymysql`` for MySQL or ``psycopg2-binary`` for
PostgreSQL.

::

   $ pip install pymysql

::

   $ pip install psycopg2-binary
