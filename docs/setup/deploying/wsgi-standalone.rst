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

__ https://gunicorn.org/

uWSGI
-----

`uWSGI`__ is a fast application server written in C. It is very configurable
which makes it more complicated to setup than gunicorn.

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
