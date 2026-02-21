Templates
=========

Templates in Liara are used to style content. There are two parts to every template, the first is the definition which describes which template should get applied to which URL, and the template execution environment which provides the content that will be consumed by the template.

Definition
----------

Templates are defined using a template definition, which must contain at least two fields:

* ``backend`` selects the template engine. This must be one of:

  - ``jinja2``: Uses `Jinja2 <https://jinja.palletsprojects.com>`_. This is the default.
  - ``mako``: Uses `Mako <https://www.makotemplates.org/>`_

* ``paths`` provides a dictionary containing key-value pairs. See  :any:`path patterns <path-patterns>` for more details.

* ``backend_options`` contains a mapping of options to be passed to the backend. For example, for Jinja2, if you want to keep the trailing newline, you'd set:

  .. code:: yaml

    backend_options:
      jinja2:
        keep_trailing_newline: true


  Currently, only the Jinja2 backend has options that can be set this way. The default options that are set to enabled are ``trim_blocks`` and ``lstrip_blocks``. You can set any `Jinja2 option <https://jinja.palletsprojects.com/en/3.0.x/api/?highlight=environment#jinja2.Environment>`_ that doesn't expect a Python object. Additionally, ``enable_async`` can't be toggled.

A very basic template could be defined as following:

.. code:: yaml

   backend: jinja2
   paths:
     "/*": "default.jinja" 

This would process any page using the ``default.jinja`` template.

Template definitions also support the following fields:

* ``static_directory`` specifies static files which will be deployed to the output. This can be used for images etc.
* ``resource_directory`` specifies resource files to be deployed, for instance ``SASS`` files. See :doc:`../content/resources` for more details.
* ``image_thumbnail_sizes``: Replaced by ``image_thumbnails.sizes``, see below.

  .. deprecated:: 2.4.1

* .. _`image-thumbnails-option`:

  ``image_thumbnails`` is a dictionary used to configure image thumbnails:

  .. code:: yaml

     image_thumbnails:
      sizes:
        thumbnail-md: {width: 640}
        thumbnail-xs: {width: 320, exclude: "*.preview.*"}
        hero: {longest_edge: 500, include: "*.hero.*"}
      formats:
        - original
        - webp


  This definition will create three kinds of thumbnails. The first entry will resize any static image file (from the template or the site itself) to a maximum width of 640 pixels. The thumbnail will be stored using the same file path as the original, but with  ``thumbnail-md`` added to the suffix. For instance, an input file named ``foo.png`` with width 800 would be resized to ``foo.thumbnail-md.png`` with a width of 640. Files which are below the size will get copied, so it's always safe to use the ``.thumbnail-md`` suffix.

  Additionally, it will create files with a ``thumbnail-xs`` suffix for all files which *don't* match the exclude pattern, and ``hero`` thumbnails for all files with *do* match the include pattern. This is useful to exclude manually created thumbnails, or only create thumbnails for files which are particularly large. ``include`` and ``exclude`` are mutually exclusive, only one can be set per thumbnail size.

  The definition can use ``width`` or ``height`` (or both, in which case the smaller size is used.) Alternatively, you can use ``longest_edge`` to scale the longest edge to the desired length. In all cases, the aspect ratio will be maintained.

  ``formats`` is a list of formats to use for the thumbnails.
  ``original`` means the original format is used (determined from the file extension). Additional supported formats are: ``JPG``, ``PNG`` and ``WEBP``.

  .. versionadded:: 2.4.1
      ``formats`` and ``sizes`` were added.
  .. versionadded:: 2.5.0
      ``exclude`` and ``include`` were added.
  .. versionadded:: 2.7.6
      ``longest_edge`` was added.

.. note::

   There is nothing special about ``thumbnail-md`` in the example above -- any suffix can be used, and multiple suffixes are supported (for example, ``thumb-1x`` and ``thumb-2x`` for normal and high density screens.)



Authoring Templates
-------------------

Templates get applied to :py:class:`~liara.nodes.DocumentNode` and :py:class:`~liara.nodes.IndexNode` instances only (which are referred to as "pages" in the context of a template.) Inside a template, a few global variables are pre-populated to provide access to the site and page content. Note that the content of other nodes *cannot* be referenced inside a template (as the order in which they get executed is unspecified), however, metadata of other nodes *is* available and can be used.

- ``page`` references the current node, in form of a :py:class:`~liara.template.Page` instance.
- ``node`` provides access to the current node directly, which will point to a  :py:class:`~liara.nodes.Node` instance.
- ``site`` provides access to the site in form of the :py:class:`~liara.template.SiteTemplateProxy` object.
- ``build_context`` provides access to the :py:class:`~liara.publish.BuildContext`, which provides information about the current build like the last-modified-date of the source file.

In most cases, templates should only use the ``page`` reference as it's rarely useful to directly access the underlying node instances. One use case for accessing the nodes is for example to create a listing of all images in a folder, as images are instances of :py:class:`~liara.nodes.StaticNode`.

Path patterns
-------------

.. _path-patterns:

The paths used for template matching are using a syntax very similar to filesystem globs, with ``*`` being the only wildcard character supported. Perfect matches take precedence over wildcard matches. That is, if there are two path patterns ``/foo/*`` and ``/foo/``, and they are matched against ``/foo/``, both match but ``/foo/`` gets selected as it's a perfect match.

The patterns have two additional tie-breaker rules implemented if multiple rules apply to the same template:

* If two rules have the same score, the longer rule wins, as it's assumed to be more specific. For instance, if you have a rule ``/en*`` and ``/*``, and you match ``/en``, then both match, but because ``/en*`` is longer it gets selected.
* If rules have the same length and match the same URL, the first matching rule is used. I.e. if you specify ``/e*`` and ``/*n`` to match ``/en``, whichever rule came first in the rule set wins.

Additionally, template path patterns allow a query string to restrict the search to specific types. For instance, ``/foo/*?kind=document`` will match all :py:class:`~liara.nodes.DocumentNode` below ``/foo/``, but will ignore other node types. The nodes types that can be selected using this method are ``document`` for :py:class:`~liara.nodes.DocumentNode` instances and ``index`` for :py:class:`~liara.nodes.IndexNode` instances.

.. note::

  You can use ``inspect template-match`` to find out what template matches a given path.