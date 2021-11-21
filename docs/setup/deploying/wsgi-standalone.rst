Standalone WSGI Containers
==========================

There are popular servers written in Python that contain WSGI applications and
serve HTTP. These servers stand alone when they run; you can let your clients
access them directly or proxy to them from your web server such as Apache
or nginx.

Gunicorn
--------

`Gunicorn`__ "Green Unicorn" is a WSGI HTTP Server for UNIX. It's a pre-fork
worker model. Running Supysonic on this server is quite simple. First install
Gunicorn with either :command:`pip install gunicorn` or
:command:`apt install gunicorn3` (the ``gunicorn`` package in this case is
for Python 2 which isn't supported anymore). Then::

   $ gunicorn "supysonic.web:create_application()"

But this will only listen on the loopback interface, which isn't really useful.

Gunicorn provides many command-line options -- see :command:`gunicorn -h`.
For example, to run Supysonic with 4 worker processes (``-w 4``) binding to all
IPv4 interfaces on port 5722 (``-b 0.0.0.0:5722``)::

   $ gunicorn -w 4 -b 0.0.0.0:5722 "supysonic.web:create_application()"

.. note::

   While :command:`gunicorn` provides way more options to configure its
   behaviour than :command:`supysonic-server` will ever do, the above example is
   actually equivalent to::

      $ supysonic-server -S gunicorn --processes 4

__ https://gunicorn.org/

uWSGI
-----

`uWSGI`__ is a fast application server written in C. It is very configurable
which makes it more complicated to setup than Gunicorn.

To use it, install the package ``uwsgi`` with either :command:`pip` or
:command:`apt`. Using the later, wou might also need the additional package
``uwsgi-plugin-python3``.

Then to run Supysonic in uWSGI::

   $ uwsgi --http-socket 0.0.0.0:5722 --module "supysonic.web:create_application()"

If it complains about an unknown ``--module`` option, try adding
``--plugin python3``::

   $ uwsgi --http-socket 0.0.0.0:5722 --plugin python3 --module "supysonic.web:create_application()"

As uWSGI is highly configurable there are several options you could use to tweak
it to your liking. Detailing all it can do is way beyond the scope of this
documentation, if you're interested please refer to its documentation.

If you plan on using uWSGI behind a nginx reverse proxy, note that nginx
provides options to integrate directly with uWSGI. You'll find an example
configuration in `Flask's documentation`__ (the framework Supysonic is built
upon). Replace the ``myapp:app`` in their example by
``supysonic.web:create_application()`` (you might need to enclose it in
double-quotes).

__ https://uwsgi-docs.readthedocs.io/en/latest/
__ https://flask.palletsprojects.com/en/2.0.x/deploying/uwsgi/

Waitress
--------

`Waitress`__ is meant to be a production-quality pure-Python WSGI server with
very acceptable performance. It has no dependencies except ones which live in
the Python standard library.

As for Gunicorn, using it to run Supysonic is rather simple. Install it using
either :command:`pip install waitress` or
:command:`apt install python3-waitress`. Then start the server this way::

   $ waitress-serve --call supysonic.web:create_application

Waitress behaviour can be tuned through various command-line options -- see
:command:`waitress-serve --help`. If none of them are relevant to you,
:command:`supysonic-server` can actually be used instead::

   $ supysonic-server -S waitress

Both commands are equivalent, with the only difference being the port they
listen on.

__ https://docs.pylonsproject.org/projects/waitress/en/stable/index.html
