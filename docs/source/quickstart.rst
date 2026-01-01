Quickstart
==========

If you want to get rolling with Liara right away, here's a quickstart guide to get you started.

Installation
------------

After obtaining `pip <https://pip.pypa.io/en/stable/installation/>`_, use:

.. code:: bash

  pip install Liara

The Liara installation can be customized by adding extras to the installation. Extra features are:

* ``redis``: Enables the Redis cache backend.
* ``compression``: Enables more compression backends (Brotli on any Python version, and Zstandard on Python versions prior to 3.14.)

For instance, if you want to install Liara with Redis support, you would install ``liara[redis]``.

Create a project
----------------

Installing Liara deploys the command-line runner ``liara``, which is your entry point for all future operations. To get started, create a new folder somewhere and run:

.. code:: bash

  liara quickstart

This will deploy the required scaffolding for a super-simple blog, which we'll use throughout this guide.

Preview the site
----------------

For an interactive preview, run: 

.. code:: bash
  
  liara serve
  
This starts a local web-server which will show the generated page. You can edit pages and templates while in this mode and hit refresh to see updates.

By default, the ``serve`` command will open a server that listens on port 8080
and will open your configured browser. This can be configured from the command
line.

Build the site
--------------

To build the whole site, from the main directory, run:

.. code:: bash

  liara build
  
This will build all pages, unlike preview which only builds pages on demand. The site will be generated in an ``output`` subdirectory by default. To deploy it, you can use for example `rsync`.

Exploring the quick-start template
----------------------------------

The quickstart produces a bunch of folders and files:

* ``content`` holds the content, which for the quickstart sample consists of a few blog posts. See :doc:`content/content` for more details on how to structure the content.
* ``templates`` holds the template files. The quickstart sample uses `Jinja2 <https://jinja.palletsprojects.com>`_ for its templates, but you can select the template engine using the command line to use `Mako <https://www.makotemplates.org/>`_ instead. ``default.yaml`` in that folder contains the default routes for the templates. See :doc:`publish/templates` for more information on how to use templates.
* ``generators`` contains a sample generator to create new blog posts. See :doc:`content/generators` for more information.
* A few :ref:`configuration files <configuration>`.