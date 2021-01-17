Apache and mod_wsgi
===================

If you are using the `Apache`__ webserver, you can use it to run Supysonic with
the help of `mod_wsgi`__.

__ https://httpd.apache.org/
__ https://github.com/GrahamDumpleton/mod_wsgi

Installing `mod_wsgi`
---------------------

If you don't have `mod_wsgi` installed yet you have to install it and enable it
first as follows::

   # apt install libapache2-mod-wsgi-py3
   # a2enmod wsgi

Creating a `.wsgi` file
-----------------------

To run Supysonic within Apache you need a :file:`supysonic.wsgi` file. Create
one somewhere and fill it with the following content:

.. code-block:: python3

   from supysonic.web import create_application
   application = create_application()

Store that file somewhere that you will find it again (e.g.:
:file:`/var/www/supysonic/supysonic.wsgi`).

Configuring Apache
------------------

The last thing you have to do is to edit the Apache configuration to tell it to
load the application. Here's a basic example of what it looks like:

.. code-block:: apache

   WSGIScriptAlias /supysonic /var/www/supysonic/supysonic.wsgi
   <Directory /var/www/supysonic>
      WSGIApplicationGroup %{GLOBAL}
      WSGIPassAuthorization On
      Require all granted
   </Directory>

With that kind of configuration, the server address will look like
`http://server/supysonic/`.

For more information consult the `mod_wsgi documentation`__. Note that the
``WSGIPassAuthorization`` directive is required for some clients as they provide
their credentials using the *basic access authentification* mechanism rather
than as URL query parameters.

__ https://modwsgi.readthedocs.io/en/latest/
