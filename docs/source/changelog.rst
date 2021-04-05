Changelog
=========

2.1.0
-----

* Introduce a new plugin system. This moves the ``has-pending-document`` command into a new plugin and adds signals to interact with liara's processing. See :doc:`plugins` for details.
* Remove ``liara.version.version`` in favor of the more standard ``liara.__version__`` variable.

2.0.7
-----

* Add a ``server_rule_only`` option to prevent the creation of redirection nodes and use the redirection paths verbatim.

2.0.6
-----

* Add ``has-pending-document`` to the command line. This will check if there is any content which is filtered by the :py:class:`~liara.site.DateFilter`. This is useful for cron-based deploys which try to not rebuild if there are no content changes, as there is no other way to find out if all content in a given revision has been published.

2.0.5
-----

* Fixed ``liara create-config`` not working.

2.0.4
-----

* Added :py:class:`~liara.cache.Sqlite3Cache`, which allows caching everything into a single file instead of one file per entry.
* Added a bytecode cache for the :py:class:`~liara.template.Jinja2TemplateRepository`.
* Fixed generated nodes not getting generated when using ``liara serve``.
* Reduced debug spew when stopping ``liara serve`` using ``^C``.

2.0.3
-----

* Added :py:meth:`~liara.template.SiteTemplateProxy.get_page_by_url`.

2.0.2
-----

* Fixed a packaging issue.

2.0.1
-----

* Improved document handling: Documents without a trailing newline are now supported, previously they would cause an error.
* Improved configuration: Empty configuration files are now supported.
* Fixed ``list-files`` requiring a type to be specified.
* Added :py:meth:`~liara.query.Query.exclude`.
* Override ``base_url`` when serving locally. This was previously documented to work, but not implemented. As part of this change, :py:meth:`~liara.site.Site.set_metadata_item` was added.

2.0
---

liara 2.0 is a complete rewrite of liara, with no shared code with the 1.x series. liara 2 is now template & content driven, and no longer just a library which simplifies static page generation. Unlike the 1.x series, it is possible to use liara 2 without writing any Python code.