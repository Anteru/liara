Changelog
=========

2.0.3
-----

* Added :py:meth:`~liara.template.SiteTemplateProxy.get_page_by_url`.

2.0.2
-----

* Fix a packaging issue.

2.0.1
-----

* Improved document handling: Documents without a trailing newline no longer result in a failure.
* Improved configuration: Empty configuration files no longer cause an error.
* Fixed ``list-files`` requiring a type to be specified.
* Added :py:meth:`~liara.query.Query.exclude`.
* Override ``base_url`` when serving locally. This was previously documented to work, but not implemented. As part of this change, added :py:meth:`~liara.site.Site.set_metadata_item`.

2.0
---

liara 2.0 is a complete rewrite of liara, with no shared code with the 1.x series. liara 2 is now template & content driven, and no longer just a library which simplifies static page generation. Unlike the 1.x series, it is possible to use liara 2 without writing any Python code.