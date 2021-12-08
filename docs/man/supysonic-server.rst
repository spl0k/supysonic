supysonic-server
================

SYNOPSIS
--------

supysonic-server [**--server** *gevent* | *gunicorn* | *waitress*] [**--host** <*hostname*>] [**--port** <*port*>] [**--socket** <*path*>] [**--processes** <*n*>] [**--threads** <*n*>]

DESCRIPTION
-----------

**supysonic-server** is the main supysonic's component, allowing to serve
content to clients. It is actually a basic wrapper over **Gevent**, **Gunicorn**
or **Waitress**, requiring at least one of them to be installed to run.

OPTIONS
-------

**-S** <*name*>, **--server** <*name*>
    Specify which WSGI server to use. <*name*> must be one of ``gevent``,
    ``gunicorn`` or ``waitress`` and the matching package must then be
    installed. If the option isn't provided, the first one available will be
    used.

**-h** <*hostname*>, **--host** <*hostname*>
    Hostname or IP address on which to listen. The default is ``0.0.0.0`` which
    means to listen on all IPv4 interfaces on this host.
    Cannot be used with **--socket**.

**-p** <*port*>, **--port** <*port*>
    TCP port on which to listen. Default is ``5722``.
    Cannot be used with **--socket**.

**-s** <*path*>, **--socket** <*path*>
    Path of a Unix socket on which to bind to. If a path is specified, a Unix
    domain socket is made instead of the usual inet domain socket.
    Cannot be used with **--host** or **--port**.
    Not available on Windows.

**--processes** <*n*>
    Number of worker processes to spawn. Only applicable when using the
    **Gunicorn** WSGI server.

**--threads** <*n*>
    The number of worker threads for handling requests. Only applicable when
    using the **Gunicorn** or **Waitress** WSGI server.

BUGS
----

Bugs can be reported to your distribution's bug tracker or upstream at
https://github.com/spl0k/supysonic/issues.

SEE ALSO
--------

``supysonic-cli (1)``
