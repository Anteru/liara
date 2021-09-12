URL patterns
============

.. _url-patterns:

In various places Liara allows matching content by URL pattern. This is very similar to matching files using a glob pattern, the syntax is as following:

* ``*`` matches anything but a subpath (i.e., ``/foo/*`` will match ``/foo/bar``, but not ``/foo/bar/baz``)
* ``**`` matches anything recursively (i.e. ``/foo/**`` will match any path starting with ``/foo/``)

Perfect matches take precedence over wildcard matches. That is, if there are two URL patterns ``/foo/*`` and ``/foo/``, and they are matched against ``/foo/``, both match but ``/foo/`` gets selected as it's a perfect match.

The URL patterns have two tie-breaker rules implemented if multiple rules apply to the same template:

* If two rules have the same score, the longer rule wins, as it's assume to be more specific. For instance, if you have a rule ``/en*`` and ``/*``, and you match ``/en``, then both match, but because ``/en*`` is longer it's assume to be a better match.
* If rules have the same length and match the same URL, the first matching rule is used. I.e. if you specify ``/*`` twice in a list of URL patterns, then the *first* entry wins.

Additionally, URL patterns allow a query string to restrict the search to specific types. For instance, ``/foo/**?kind=document`` will match all :py:class:`~liara.nodes.DocumentNode` below ``/foo/``, but will ignore other node types. The nodes types that can be selected using this method are ``document`` for :py:class:`~liara.nodes.DocumentNode` instances and ``index`` for :py:class:`~liara.nodes.IndexNode` instances.