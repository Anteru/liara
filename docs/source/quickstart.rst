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

For instance, if you want to install Liara with Redis support, you would install ``liara[redis]``.

Create a project
----------------

Installing Liara deploys the command-line runner ``liara``, which is your entry point for all future operations. To get started, create a new folder somewhere and run:

.. code:: bash

  liara quickstart

This will deploy the required scaffolding for a super-simple blog, which we'll use throughout this guide.

Build the site
--------------

From the main directory, run ``liara build`` to build the site. The site will be generated in an ``output`` subdirectory by default.

Preview the site
----------------

Run ``liara serve`` to run a local web-server which will show the page. You can edit pages and templates while in this mode and hit refresh to see updates. You cannot add/remove content or change meta-data while running the interactive server though.

Exploring the quick-start template
----------------------------------

The quickstart produces a bunch of folders and files:

* ``content`` holds the content, which for the quickstart sample consists of a few blog posts. See :doc:`content` for more details on how to structure the content.
* ``templates`` holds the template files. The quickstart sample uses jinja2 for its templates. ``default.yaml`` in that folder contains the default routes for the templates. See :doc:`templates` for more information on how to use templates.
* ``generators`` contains a sample generator to create new blog posts. See :doc:`generators` for more information.
* A few :ref:`configuration files <configuration>`.