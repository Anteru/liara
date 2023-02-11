Configuration
=============

.. _configuration:

Liara is driven through configuration files. The main file is ``config.yaml``, which can reference other configuration files. To get the full default configuration, use ``liara create-config``. Nested configuration options can be either provided by actually nesting them in the ``YAML`` file, or by ``.`` as the separator. For example, the following two configurations are equivalent:

.. code-block:: yaml

  build:
    cache:
      type: redis
      redis:
        expiration_time: 60

.. code-block:: yaml

  build:
    cache.type: redis
    cache.redis.expiration_time: 60

Directory settings
------------------

* ``content_directory``: The root directory for all content. Output paths will be build relative to this folder. See :doc:`content/content` for more details.
* ``resource_directory``: The folder containing resources, i.e. ``SASS`` or other files that need to get processed before they can be written to the output. See :doc:`content/resources` for more details.
* ``static_directory``: The folder containing static files, for instance downloads, images, videos etc.
* ``output_directory``: The output directory.
* ``generator_directory``: The folder containing :doc:`content/generators`.
* ``plugin_directories``: A list of directories to be scanned for :doc:`reference/plugins`.

  .. versionadded:: 2.5

Build settings
--------------

* ``build.clean_output``: If set to ``True``, the output directory will be deleted on every build.
* ``build.cache_directory``: The directory where the cache will be stored. Only used by ``db`` and ``fs`` caches.

  .. deprecated:: 2.2
    Use ``build.cache.db.directory`` and ``build.cache.fs.directory`` instead.

* ``build.cache_type``: The cache type to use.

  .. deprecated:: 2.2
     Use ``build.cache.type``.

* ``build.cache.type``: The cache type to use. One of:

  - ``db`` uses a local database cache, which stores everything in a single file.
  - ``fs`` stores files in a directory, using one file per cache entry.
  - ``redis`` uses Redis as the backend.
  - ``none`` disables caching

  .. note::

    The ``fs`` cache is a good default for most users. If creating files is expensive, ``db`` will perform better as it stores all data in a single file. Both ``fs`` and ``db`` caches are single-user only and don't remove old entries -- if the cache grows too big, you'll want to delete the cache directory.
    
    ``redis`` is useful if you have an existing instance already, want to benefit from automatic cache clearing, or have multiple concurrent instances of Liara (for example, an automated build server in addition to a local client.)

* .. _`sass-compiler-option`:

  ``build.resource.sass.compiler``: The compiler to use for SASS files:

  - ``cli`` uses the ``sass`` command, which must be available in the path.
  - ``libsass`` uses ``libsass``, which is `deprecated <https://sass-lang.com/libsass>`_, but does not depend on external binaries.

  .. versionadded:: 2.3.4

Database cache options
^^^^^^^^^^^^^^^^^^^^^^

These options are only available when the ``cache_type`` is set to ``db``:

* ``build.cache.db.directory``: The directory where the cache will be stored.

Filesystem cache options
^^^^^^^^^^^^^^^^^^^^^^^^

These options are only available when the ``cache_type`` is set to ``fs``:

* ``build.cache.fs.directory``: The directory where the cache will be stored.

Redis cache options
^^^^^^^^^^^^^^^^^^^

These options are only available when the ``cache_type`` is set to ``redis``:

* ``build.cache.redis.host``: The Redis host string (default: ``localhost``)
* ``build.cache.redis.port``: The Redis port (default: ``6379``)
* ``build.cache.redis.db``: The Redis DB (default: ``0``)
* ``build.cache.redis.expiration_time``: The expiration time for cache values in minutes (default: ``60``)

Content settings
----------------

* ``content.filters``: Specifies which :any:`content filters <content-filters>`  will be applied while discovering content.
* ``template``: The :any:`template <publish/templates>` definition to apply to the content.
* ``collections``: Points to the file containing the :doc:`collection <content/collections>` definitions.
* ``feeds``: Points to the file containing the :doc:`feed definitions <publish/feeds>`.
* ``indices``: Points to the file containing the :doc:`index definitions <content/indices>`.
* ``metadata``: Points to the file containing the :doc:`site metadata <content/metadata>`.
* ``relaxed_date_parsing``: If enabled, metadata fields named ``date`` will be processed twice. By default, Liara assumes that ``date`` contains a markup-specific date field. If this option is on, and the ``date`` field is pointing at a string, Liara will try to parse that string into a timestamp.
* ``allow_relative_links``: Allow the usage of relative links in content files. This has a negative build time impact on any file containing relative links and is thus recommended to be left off.
* ``content.markdown``: Configures the Markdown processor. Liara uses `Python-Markdown <https://python-markdown.github.io/>`_ with  `PyMdown Extensions <https://facelessuser.github.io/pymdown-extensions/>`_ for Markdown processing. You can set the extension list, the extension configuration, and the output format here.

  This option is a dictionary with three keys:

  - ``extensions``: A list of extensions to enable.
  - ``config``: This is mapped to the ``extension_config`` variable and can be used to fine-tune the extension behavior.
  - ``output``: Configures the `output format <https://python-markdown.github.io/reference/#output_format>`_. The default is ``html5``.

  .. versionadded:: 2.5

Other settings
--------------

* ``routes.static``: Points to the file containing :any:`static routes <publish/static-routes>`.
* ``ignore_files``: A list of file patterns to ignore, for instance, ``["*.backup"]``. The default is ``*~`` which ignores all files with a trailing ``~``. The file matching supports Unix-style wildcards: ``?`` matches a single character, ``*`` matches everything.
