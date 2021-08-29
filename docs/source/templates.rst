Templates
=========

Templates in Liara are used to style content. There are two parts to every template, the first is the definition which describes which template should get applied to which URL, and the template execution environment which provides the content that will be consumed by the template.

Definition
----------

Templates are defined using a template definition, which must contain at least two fields:

* ``backend`` chose the template engine, the default is ``jinja2``.
* ``paths`` provides a dictionary containing key-value pairs. The key must be an :doc:`URL pattern <url-patterns>`, the value the template file that should get applied for this pattern.

A very basic template could be defined as following:

.. code:: yaml

   backend: jinja2
   paths:
     "/*": "default.jinja" 

This would process any page using the ``default.jinja`` template.

Template definitions also support the following fields:

* ``static_directory`` specifies static files which will be deployed to the output. This can be used for images etc.
* ``resource_directory`` specifies resource files to be deployed, for instance ``SASS`` files.
* ``image_thumbnail_sizes`` is a dictionary which provides suffixes and the sizes to which images get resized. For instance, assume the following configuration:

  .. code:: yaml

     image_thumbnail_sizes:
       thumbnail: {width: 640}

  This will resize any static image file (from the template or the site itself) to a maximum width of 640 pixels. The thumbnail will be stored using the same file path as the original, but with  ``thumbnail`` added to the suffix. For instance, an input file named ``foo.png`` with width 800 would be resized to ``foo.thumbnail.png`` with a width of 640. Files which are below the size will get copied, so it's always safe to use the ``.thumbnail`` suffix.

.. note::

   There is nothing special about ``thumbnail`` in the example above -- any suffix can be used, and multiple suffixes are support.

Authoring Templates
-------------------

Templates get applied to :py:class:`~liara.nodes.DocumentNode` and :py:class:`~liara.nodes.IndexNode` instances only. Inside a template, a few global variables are pre-populated to provide access to the site and page content. Note that the content of other nodes *cannot* be referenced inside a template (as the order in which they get executed is unspecified), however, metadata of other nodes *is* available and can be used.

- ``page`` references the current node, in form of a :py:class:`~liara.template.Page` instance.
- ``node`` provides access to the current node directly, which will point to a  :py:class:`~liara.nodes.Node` instance.
- ``site`` provides access to the site in form of the :py:class:`~liara.template.SiteTemplateProxy` object.
