Changelog
=========

2.2.0
-----

* Bump minimal required Python version to 3.8.

2.1.3
-----

* Fix ``liara quickstart`` not working.
* Fix a bug when fixing up timezones while using the ``zoneinfo`` package for timezone data.

2.1.2
-----

* Deprecate :py:attr:`liara.template.Page.meta` in favor of :py:attr:`liara.template.Page.metadata` (which was newly added in this version) for consistency with :py:attr:`liara.template.SiteTemplateProxy.metadata`.
* Use the logger in ``liara serve`` instead of printing directly to the console for log messages. The default listen URL will be still printed if showing the browser is disabled.
* Set the ``Content-Type`` header in ``liara serve``. This fixes an issue with Chrome/Edge where SVG images whould not work as they were served without a content type.
* Update ``jinja2`` dependency to `3.0 <https://jinja.palletsprojects.com/en/3.0.x/changes/#version-3-0-0>`_. This provides access to new Jinja2 features like required blocks.
* Update ``click`` dependency to `8.0 <https://click.palletsprojects.com/en/8.0.x/changes/#version-8-0-0>`_.

2.1.1
-----

* Fix plugins not being packaged.

2.1.0
-----

* Introduce a new plugin system. This moves the ``has-pending-document`` command into a new plugin and adds signals to interact with liara's processing. See :doc:`plugins` for details.
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