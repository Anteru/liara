Collections
===========

A collection in Liara groups content together into an optionally ordered collection. This grouping is efficient, i.e. iterating a sorted collection does not incur any sorting cost. It is also efficient to look up the next/previous entry in an collection.

Definition
----------

A collection definition consists of the following elements:

- The name (that's the key used in the YAML file)
- ``filter``: The filter -- this is an :ref:`URL pattern <url-patterns>` which defines all elements that are in this collection.
- ``order_by``: The ordering -- optionally specifies how the collection should be ordered. This is a metadata accessor, to access nested fields, separate the individual accesses using ``.``. For instance, ``date.year`` will access the ``date`` metadata field first, and then the ``year`` attribute. If you want to reverse the order, add a leading ``-``, for example ``-date.year``. If the metadata is missing, an error will be raised. Use ``exclude_without`` if you want to remove items which don't have certain metadata fields. Multiple fields can be specified by using a list.
- ``exclude_without``: Optionally exclude nodes without the specified metadata field(s). Multiple fields can be specified by using a list.
- ``node_kinds``: The node kinds to include -- optionally, the kinds of nodes to include in the collection can be specified. If nothing is specified, only document nodes are included by default.

For example:

.. code:: yaml

  blog:
    filter: '/blog/**'
    order_by: 'date'
    exclude_without: 'date'

Defines a collection named ``blog``, which contains all elements under ``/blog``, ordered by the ``date`` metadata field. Documents which don't contain a ``date`` metadata entry are filtered out.

.. note::

  Without the ``exclude_without`` filter, documents without a ``date`` metadata field would cause an error.

Usage
-----

Collections can be used in two places, templates and indices. In a template, you can retrieve all pages in a collection by using using :py:meth:`~liara.template.SiteTemplateProxy.get_collection`. This returns a :py:class:`~liara.query.Query` object which can be used to iterate over the set of pages. If a collection is ordered, :py:meth:`~liara.template.SiteTemplateProxy.get_next_in_collection` and :py:meth:`~liara.template.SiteTemplateProxy.get_previous_in_collection` can be used to provide next/previous links for documents which are part of a collection.

The other use of collections is to create an index. See :doc:`indices` for more details.