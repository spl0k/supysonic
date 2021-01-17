Other options
=============

FastCGI
-------

FastCGI is a deployment option on servers like `nginx`__ or `lighttpd`__; see
:doc:`wsgi-standalone` for other options.
To use Supysonic with any of them you will need a FastCGI server first. The most
popular one is `flup`__ which we will use for this guide. Make sure to have it
installed (with eith :command:`pip` or :command:`apt`) to follow along.

__ https://nginx.org/
__ https://www.lighttpd.net/
__ https://pypi.org/project/flup/

Creating a `.fcgi` file
^^^^^^^^^^^^^^^^^^^^^^^

First you need to create the FastCGI server file. Let's call it
:file:`supysonic.fcgi`:

.. code-block:: python3

   #!/usr/bin/python3

   from flup.server.fcgi import WSGIServer
   from supysonic.web import create_application

   if __name__ == "__main__":
      app = create_application()
      WSGIServer(app).run()

This should be enough for Apache to work, however nginx and older versions of
lighttpd need a socket to be explicitly passed to communicate with the
FastCGI server. For that to work you need to pass the path to the socket
to the :py:class:`~flup.server.fcgi.WSGIServer`:

.. code-block:: python3

   WSGIServer(app, bindAddress="/path/to/fcgi.sock").run()

The path has to be the exact same path you define in the server
config.

Save the :file:`supysonic.fcgi` file somewhere you will find it again.
It makes sense to have that in :file:`/var/www/supysonic` or something
similar.

Make sure to set the executable bit on that file so that the servers
can execute it::

   $ chmod +x /var/www/supysonic/supysonic.fcgi

Configuring the web server
^^^^^^^^^^^^^^^^^^^^^^^^^^

The example above is good enough for a basic Apache deployment but your
`.fcgi` file will appear in your application URL e.g.
``example.com/supysonic.fcgi/``. If that bothers you or you wish to load it in
another web server, Flask's documentation details how to do it for `Apache`__,
`lighttpd`__ or `nginx`__.

__ https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-apache
__ https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-lighttpd
__ https://flask.palletsprojects.com/en/1.1.x/deploying/fastcgi/#configuring-nginx

CGI
---

If all other deployment methods do not work, CGI will work for sure.
CGI is supported by all major servers but usually has a sub-optimal
performance.

Creating a `.cgi` file
^^^^^^^^^^^^^^^^^^^^^^

First you need to create the CGI application file. Let's call it
:file:`supysonic.cgi`:

.. code-block:: python3

   #!/usr/bin/python3

   from wsgiref.handlers import CGIHandler
   from supysonic.web import create_application

   app = create_application()
   CGIHandler().run(app)

Server Setup
^^^^^^^^^^^^

Usually there are two ways to configure the server.  Either just copy the
``.cgi`` into a :file:`cgi-bin` (and use `mod_rewrite` or something similar to
rewrite the URL) or let the server point to the file directly.

In Apache for example you can put something like this into the config:

.. code-block:: apache

   ScriptAlias /supysonic /path/to/the/supysonic.cgi
