Templates
=========

Templates in Liara are used to style content. There are two parts to every template, the first is the definition which describes which template should get applied to which URL, and the template execution environment which provides the content that will be consumed by the template.

Definition
----------

Templates are defined using a template definition, which must contain at least two fields:

* ``backend`` selects the template engine. This must be one of:

  - ``jinja2``: Uses `Jinja2 <https://jinja.palletsprojects.com>`_. This is the default.
  - ``mako``: Uses `Mako <https://www.makotemplates.org/>`_

* ``paths`` provides a dictionary containing key-value pairs. See  `path patterns <path-patterns>`_ for more details.

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

Path patterns
-------------

.. _path-patterns:

The paths used for template matching are using a syntax very similar to filesystem globs, with ``*`` being the only wildcard character supported. Perfect matches take precedence over wildcard matches. That is, if there are two path patterns ``/foo/*`` and ``/foo/``, and they are matched against ``/foo/``, both match but ``/foo/`` gets selected as it's a perfect match.

The patterns have two additional tie-breaker rules implemented if multiple rules apply to the same template:

* If two rules have the same score, the longer rule wins, as it's assumed to be more specific. For instance, if you have a rule ``/en*`` and ``/*``, and you match ``/en``, then both match, but because ``/en*`` is longer it gets selected.
* If rules have the same length and match the same URL, the first matching rule is used. I.e. if you specify ``/e*`` and ``/*n`` to match ``/en``, whichever rule came first in the rule set wins.

Additionally, template path patterns allow a query string to restrict the search to specific types. For instance, ``/foo/*?kind=document`` will match all :py:class:`~liara.nodes.DocumentNode` below ``/foo/``, but will ignore other node types. The nodes types that can be selected using this method are ``document`` for :py:class:`~liara.nodes.DocumentNode` instances and ``index`` for :py:class:`~liara.nodes.IndexNode` instances.