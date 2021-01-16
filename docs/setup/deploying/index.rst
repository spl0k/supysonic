Running the web server
======================

Once Supysonic is installed and configured, you'll have to start its web server
for the clients to be able to access the music. Here you have several options,
whether you want to run it as independant process(es), then possibly putting it
behind a reverse proxy, or running it as a WSGI application within Apache.

You'll find some common (and less common) deployment option below:

.. toctree::
   :maxdepth: 2

   wsgi-standalone
   apache
   other

As Supysonic is a WSGI application, you have numerous deployment options
available to you. If you want to deploy it to a WSGI server not listed here,
look up the server documentation about how to use a WSGI app with it. When
setting one of those, you'll want to call the :func:`create_application` factory
function from module :mod:`supysonic.web`.
