Metadata
========

The default site metadata consists of:

* ``title``: The site title.
* ``description``: A description of the site.
* ``base_url``: The default URL this page will get deployed to. liara may
  replace this with a different URL when serving the page locally.
* ``language``: The language, provided as a language code of the form ``en-US``.
* ``copyright``: The default content copyright.

Metadata is used throughout Liara, for instance, :doc:`feeds` may use the metadata. It is available through :py:attr:`~liara.site.Site.metadata` within liara, and via :py:attr:`~liara.template.SiteTemplateProxy.metadata` to templates.