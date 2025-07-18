Changelog
=========

2.7.1
-----

* Fix ``liara serve`` failing to serve paths which are URL-encoded, for example, paths containing spaces escaped using ``%20``.
* Fix an error when creating thumbnails for two files with the same base filename (i.e. without the extension.) In this case, a debug message is printed, and the second set of thumbnails is not generated. This would occur if you had two files, ``foo.png`` and ``foo.webp``, and liara would try to generate a ``foo.thumbnail.webp`` file for the ``.png``, and then create the same file again for the ``.webp`` file.
* Fix data files not getting merged properly. Previously, two data files, one containing ``key: { value1: ...}`` and one containing ``key: { value2: ...}`` would not merge correctly, so the resulting dictionary contained ``key: { value1: ...}`` or ``key: { value2: ...}`` depending on the order they were processed. In 2.7.1, the expected result is created instead, which is: ``key: { value1: ..., value2: ...}``.
* Shortcode names can include dashes now, i.e. ``foo-bar`` is now a valid shortcode name.

2.7.0
-----

* Add a new ``ìnspect`` command. This is useful for debugging internal state:

  * ``inspect data`` can be used to inspect the :py:attr:`~liara.site.Site.merged_data` content.
  * ``inspect template-match`` can be used to check a template pattern, see :doc:`../publish/templates`.

* Change how ``serve`` works: Previously, ``serve`` would miss certain changes to the web site (like adding new files or changing data files.) The new implementation recreates the whole state allowing any change to be done during development.

2.6.4
-----

* Fix ``$data`` not being present in shortcodes when using ``liara validate-links``.

2.6.3
-----

* Fix ``$data`` not being present in shortcodes when using ``liara serve``.

2.6.2
-----

* Improve cache robustness: Previously, configuration, plugin or data changes would not  invalidate the cache, so it had to be cleared manually. This should no longer be necessary.
* The cache is now persisted when using ``liara serve``. This improves performance when calling ``liara serve`` repeatedly, as entries are cached between invocations.
* ``$data`` is provided as an additional context to shortcodes. See :doc:`../content/shortcodes` for more details.
* Added ``json`` support for ``list-content``.
* Various properties have been properly marked as read-only.

2.6.1
-----

* Fix ``.yaml`` files with UTF-8 content not being read correctly. Now, files with a BOM are correctly recognized, and files without a BOM are assumed to be ``UTF-8`` encoded.
* Fix :py:class:`~liara.query.Query` failure when a filter is used in
  conjunction with ``reverse``, but without specifying a sort order.
* Fix :py:meth:`~liara.util.readtime` ignoring the ``words_per_minute`` parameter.
* Fix ``validate-links`` failing on empty documents due to an incorrect assertion.

2.6.0
-----

* Bump minimum Python version to 3.10.
* Improve log output for shortcodes. Use ``--debug`` to see information about each shortcode invocation.

2.5.4
-----

* Provide the current node as a  context variable to shortcode handlers. See :doc:`../content/shortcodes` for details.

2.5.3
-----

* Rewrite the :py:class:`~liara.md.ShortcodePreprocessor`. This resolves many issues with the existing preprocessor, for example:

  * Quoted strings containing ``/%>`` are handled correctly now.
  * Multiple shortcodes can be used in one line.
  * No whitespace is needed before the closing tag.
  * Non-quoted values can contain ``-`` now (previously, it was an alphanumeric characters or ``_`` only)
  * Parsing robustness has generally improved with better error messages.

  See :doc:`../content/shortcodes` for more details.

2.5.2
-----

* Fix the :py:data:`~liara.signals.commandline_prepared` signal not specifying a ``sender``, unlike all other signals.
* Improve documentation of signals & plugins. See :doc:`../reference/plugins` for more details.

2.5.1
-----

* Add ``exclude`` and ``include`` to thumbnail definitions to skip creation of thumbnails for some images. See :doc:`../publish/templates` for more details.

2.5.0
-----

* Add support for "shortcodes", that is, function calls embedded in the document source. See :doc:`../content/shortcodes` for more details.
* Add a new configuration option to load plugins from a directory. See :doc:`../reference/plugins` for more details.
* Documents which fail to parse don't abort the build any more. Instead, a warning will be printed pointing to the broken document, and the processing will continue.
* Markdown extensions can be configured now. See :doc:`../configuration` for more details. As part of this change, the default output format changed to ``html5`` (previously it was ``xhtml``.)
* Add a new ``build_context`` global variable to templates. See :doc:`../publish/templates` for more details.

2.4.1
-----

* Add support for parallel node processing. This can result in significantly faster build times for sites with many resources. You can use ``--no-parallel`` to disable parallel processing in case this causes problems.
* Add support for additional thumbnail formats. This also replaces the old mechanism using ``image_thumbnail_sizes`` with a new configuration setting, ``image_thumbnails``. See :doc:`../publish/templates` for more details.
* Use ``tomllib`` on Python 3.11 instead of ``tomli``.
* The :py:class:`~liara.cache.RedisCache` uses transactions now to avoid problems with concurrent access to individual cache items.

2.4.0
-----

.. note::

  This release contains breaking changes when using indices and collections. Make sure to review the changelog and the :doc:`../content/collections` and :doc:`../content/indices` pages when running into issues after updating.

  The main change is that missing metadata fields in collections and indices result in an error now, instead of silently removing items. Use ``exclude_without`` to filter nodes missing specific metadata fields. When updating from < 2.4, you can simply copy the ``order_by``/``group_by`` entry in the respective YAML file into ``exclude_without`` to get the original behavior back.

* Add :py:meth:`Query.with_node_kinds <liara.query.Query.with_node_kinds>` and :py:meth:`Query.without_node_kinds <liara.query.Query.without_node_kinds>` to :py:class:`~liara.query.Query`. This allows lists of nodes (as returned by :py:meth:`~liara.template.SiteTemplateProxy.select` and other functions) to be filtered by the node kind. This is useful if you want to mix static content and documents in the same folder.
* Add :py:meth:`SiteTemplateProxy.select_pages <liara.template.SiteTemplateProxy.select_pages>` and :py:attr:`Page.children <liara.template.Page.children>` to select pages (i.e. document and index nodes) only without having to manually filter the result using ``with_node_kinds``/``without_node_kinds``.
* Add ``node_kinds`` to :py:meth:`Collection.__init__ <liara.site.Collection.__init__>` to allow constraining a collection to a specific node kind. See :doc:`../content/collections` for more details.
* Add ``exclude_without`` to :py:meth:`Collection.__init__ <liara.site.Collection.__init__>` and :py:meth:`Index.__init__ <liara.site.Index.__init__>` to allow excluding items without a specific metadata field.
* Improve the debug output during publishing. The template publisher will now print which document is published using which template. As part of this change, :py:attr:`Template.path <liara.template.Template.path>` was added.
* Change how :py:meth:`Page.references <liara.template.Page.references>` is populated for *top level indices*. Previously, ``references`` would not be populated for a top-level index. Additionally, improve the documentation of top-level indices, see :doc:`../content/indices` for more details.
* Improve error handling when trying to sort nodes which are missing the corresponding metadata key, for example, using :py:meth:`~liara.query.Query.sorted_by_title`. Previously, this would raise an exception about a failed comparison involving ``None``, now this raises a more useful exception which contains the path to the item missing the metadata key and which key was requested.

2.3.5
-----

* Add ``--no-cache`` option to ``liara serve`` and ``liara build`` (off by
  default.)

  In some cases, it may be necessary to disable the cache to ensure up-to-date output during development. For instance ``SASS`` files can have includes which are not tracked by ``liara`` and fail to trigger a rebuild. With ``--no-cache`` each file is rebuilt on each request. This can be very slow and is thus only recommended during template/style development.

* Improve the ``liara validate-links`` command:

  * Check internal links by default. Previously, if run without ``-t``, no links were checked.
  * Return a non-zero exit code if broken links are found
  * Add more debug output
  * Fix an issue which prevented timeouts from being reported correctly.

2.3.4
-----

* Add a new configuration option to select the SASS compiler. See :ref:`configuration <sass-compiler-option>` for details.

  .. note::

    The option is set to ``libsass`` by default for now, but it is highly recommended to `install the command line compiler <https://sass-lang.com/install>`_ and use it. The option to use ``libsass`` will be removed in a future release.

* Add support for caching to :py:class:`~liara.nodes.SassResourceNode`. This can significantly speed up building sites with large amounts of SASS files.
* Change the default log formatting settings:

  * The default output no longer includes the source. The source refers (typically) to the class producing the log message and results in noise for most normal use of Liara.
  * The verbose output includes the message severity now. This makes it easier to spot warnings and errors in the verbose output.
  * The debug output level contains both the source and the severity.

2.3.3
-----

* Improve error handling during publishing. A generated node that fails to produce content is now skipped and a warning is printed.
* Non-fatal issues (i.e. those which don't stop the build) use the ``warning`` log level now instead of ``error``.
* Update ``PyYAML`` dependency to `6.0 <https://github.com/yaml/pyyaml/blob/master/CHANGES>`_.
* Update ``pymdown-extensions`` dependency to `9.0 <https://facelessuser.github.io/pymdown-extensions/about/releases/9.0/>`_.
* Replace ``toml`` dependency with ``tomli`` which is TOML 1.0 compliant (``toml`` only supports TOML 0.5)
* Add Python 3.10 as an officially supported version.

2.3.2
-----

* Add a new ``--date`` option to the command line to build the site at a different date. This is useful conjunction with the :py:class:`~liara.site.DateFilter`, as it allows previewing scheduled entries.
* Improve error handling during content discovery. An error while creating a document will no longer abort the build. Additionally, instead of printing a full stack trace, an short error message containing the file path is printed. In any case, discovery continues so multiple broken documents can be identified.

2.3.1
-----

* Improve ambiguous template pattern resolution. See :doc:`../publish/templates` for details.
* Allow setting template backend options. See :doc:`../publish/templates` for details. As part of this change, the Jinja2 backend now sets ``trim_blocks`` and ``lstrip_blocks`` by default to ``True``.

2.3.0
-----

* Add a ``--port`` option to ``liara serve`` to change the listen port.
* Add an ``ignore_files`` option to ignore certain file patterns. This is particularly useful if an editor creates lock or backup files that should be ignored. See :doc:`../configuration` for details.
* The file discovery process will ignore invalid index and resource files instead of failing with an exception. An error will be logged to help find the problematic files.
* Fix ``liara list-content`` not showing the node type on ``_index`` nodes.
* Handling of metadata has changed:

  * Document metadata can be placed in a separate ``.meta`` file instead of being part of the document itself. See :doc:`../content/content` for details.
  * Separate ``.meta`` files for metadata are no longer supported in the static and resource directory. This previously didn't work as expected -- resource files with ``.meta`` files associated had the ``.meta`` file processed (which would cause a failure), and static files had the ``.meta`` file added as a separate static file. From this release on, ``.meta`` files don't get any special treatment when placed in the static or resource directory trees. Static files inside the content directory continue to support metadata files. See :doc:`../content/content` for details.

2.2.1
-----

* Mako is now installed by default, and the ``mako`` extra is gone. If you installed Liara using ``liara[mako]``, please switch to ``liara`` going forward.
* :py:attr:`liara.template.Page.content` now returns an empty string for :py:class:`~liara.nodes.IndexNode` instances. Previously, it would raise an exception.
* ``liara quickstart`` gained a new option, ``--template-backend``, which allows selecting between ``jinja2`` and ``mako`` templates.
* The collection sort order can be reversed now. See :doc:`../content/collections` for details.

2.2.0
-----

* Bump minimal required Python version to 3.8.
* ``liara serve`` now uses the cache configuration specified by the user instead of always using a filesystem cache with fixed paths.
* Add :py:class:`~liara.cache.RedisCache`, which uses `Redis <https://redis.io/>`_ as the storage backend. Using Redis in a shared environment allows multiple clients to benefit from the cache. Additionally, the Redis cache allows for cache entries to expire, so it won't accumulate garbage over time (i.e. draft posts which never get published, etc.) See :doc:`../configuration` for details on how to enable Redis. Redis also requires Liara to be installed with the ``[redis]`` option.

2.1.3
-----

* Fix ``liara quickstart`` not working.
* Fix a bug when fixing up timezones while using the ``zoneinfo`` package for timezone data.

2.1.2
-----

* Deprecate :py:attr:`liara.template.Page.meta` in favor of :py:attr:`liara.template.Page.metadata` (which was newly added in this version) for consistency with :py:attr:`liara.template.SiteTemplateProxy.metadata`.
* Use the logger in ``liara serve`` instead of printing directly to the console for log messages. The default listen URL will be still printed if showing the browser is disabled.
* Set the ``Content-Type`` header in ``liara serve``. This fixes an issue with Chrome/Edge where SVG images would not work as they were served without a content type.
* Update ``jinja2`` dependency to `3.0 <https://jinja.palletsprojects.com/en/3.0.x/changes/#version-3-0-0>`_. This provides access to new Jinja2 features like required blocks.
* Update ``click`` dependency to `8.0 <https://click.palletsprojects.com/en/8.0.x/changes/#version-8-0-0>`_.

2.1.1
-----

* Fix plugins not being packaged.

2.1.0
-----

* Introduce a new plugin system. This moves the ``has-pending-document`` command into a new plugin and adds signals to interact with Liara's processing. See :doc:`../reference/plugins` for details.
* Remove ``liara.version.version``. Use the standard ``liara.__version__`` variable instead, which was already present in earlier versions.

2.0.7
-----

* Add a ``server_rule_only`` option to prevent the creation of redirection nodes and use the redirection paths verbatim.

2.0.6
-----

* Add ``has-pending-document`` to the command line. This will check if there is any content which is filtered by the :py:class:`~liara.site.DateFilter`. This is useful for cron-based deploys which try to not rebuild if there are no content changes, as there is no other way to find out if all content in a given revision has been published.

2.0.5
-----

* Fix ``liara create-config`` not working.

2.0.4
-----

* Add :py:class:`~liara.cache.Sqlite3Cache`, which allows caching everything into a single file instead of one file per entry.
* Add a bytecode cache for the :py:class:`~liara.template.Jinja2TemplateRepository`.
* Fix generated nodes not getting generated when using ``liara serve``.
* Reduce debug spew when stopping ``liara serve`` using ``^C``.

2.0.3
-----

* Add :py:meth:`~liara.template.SiteTemplateProxy.get_page_by_url`.

2.0.2
-----

* Fix a packaging issue.

2.0.1
-----

* Improve document handling: Documents without a trailing newline are now supported, previously they would cause an error.
* Improve configuration: Empty configuration files are now supported.
* Fix ``list-files`` requiring a type to be specified.
* Add :py:meth:`~liara.query.Query.exclude`.
* Override ``base_url`` when serving locally. This was previously documented to work, but not implemented. As part of this change, :py:meth:`~liara.site.Site.set_metadata_item` was added.

2.0
---

liara 2.0 is a complete rewrite of liara, with no shared code with the 1.x series. liara 2 is now template & content driven, and no longer just a library which simplifies static page generation. Unlike the 1.x series, it is possible to use liara 2 without writing any Python code.