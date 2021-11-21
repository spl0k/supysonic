Supysonic setup
===============

This guide details the required steps to get a Supysonic instance ready to
start serving your music.

.. rubric:: TL;DR

For the impatient, here's a quick summary to get Supysonic installed and ready
to start serving (but this doesn't create any user nor specifies where your
music is located 😏). This uses `gunicorn`__, but there are
:doc:`other options <deploying/index>`.

::

   pip install supysonic
   pip install gunicorn
   supysonic-server

__ https://gunicorn.org/

.. rubric:: Table of contents

.. toctree::
   :maxdepth: 2

   install
   database
   configuration
   deploying/index
   daemon

.. _docker:

.. rubric:: Docker

Another solution rather than going through the whole setup process yourself is
to use a ready-to-use Docker image. While we don't provide images for Supysonic,
that didn't keep the community from creating some. Take a look on the
`Docker Hub`__ and pick one you like. For more details on their usage, please
refer to the readme of said images.

__ https://hub.docker.com/search?q=supysonic&type=image
