Running the web server
======================

Once Supysonic is installed and configured, you'll have to start its web server
for the clients to be able to access the music. Here you have several options,
whether you want to run it as independant process(es), then possibly putting it
behind a reverse proxy, or running it as a WSGI application within Apache.

supysonic-server
^^^^^^^^^^^^^^^^

But the easiest might be to use Supysonic's own server. It actually requires a
WSGI server library to run, so you'll first need to have either `Gevent`__,
`Gunicorn`__ or `Waitress`__ to be installed. Then you can start the server with
the following command::

   supysonic-server

And it will start to listen on all IPv4 interfaces on port 5722.

This command allows some options, more details are given on its manpage:
:doc:`/man/supysonic-server`. It is intentionally kept simple, as such it
doesn't provide much in terms of tuning. If you want more control over the
server's behavior you might as well try one of the options presentend below.

__ https://www.gevent.org
__ https://gunicorn.org/
__ https://docs.pylonsproject.org/projects/waitress/en/stable/index.html

Other options
^^^^^^^^^^^^^

You'll find some other common (and less common) deployment options below:

.. toctree::
   :maxdepth: 2

   wsgi-standalone
   apache
   other

As Supysonic is a WSGI application, you have numerous deployment options
available to you. If you want to deploy it to a WSGI server not listed here,
look up the server documentation about how to use a WSGI app with it. When
setting one of those, you'll want to call the :py:func:`create_application`
factory function from module :py:mod:`supysonic.web`.
