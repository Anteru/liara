Quickstart
==========

If you want to get rolling with Liara right away, here's a quickstart guide to get you started.

Installation
------------

Run:

.. code:: bash

  pip install Liara

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

* ``content`` holds the content. A file in the content at path ``content/foo.md`` will produce an URL ``/foo`` (or rather, ``/foo/index.html``.) ``_index.md`` is a special name which gets attached to the path of the current directory. For example, ``content/foo/_index.md`` will get routed to ``/foo``.
* ``templates`` holds the template files. The quickstart sample uses jinja2 for its templates. ``default.yaml`` in that folder contains the default routes for the templates.
* A few :ref:`configuration files <configuration>`.