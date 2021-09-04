Collections
===========

A collection in liara groups content together into an optionally ordered collection. This grouping is efficient, i.e. iterating a sorted collection does not incur any sorting cost. It is also efficient to look up the next/previous entry in an collection.

Definition
----------

A collection definition consists of three elements:

- The name
- The filter -- this is an :ref:`URL pattern <url-patterns>` which defines all elements that are in this collection.
- The ordering -- optionally specifies how the collection should be ordered. This is a metadata accessor, to access nested fields, separate the individual accesses using ``.``. For instance, ``date.year`` will access the ``date`` metadata field first, and then the ``year`` attribute. If you want to reverse the order, add a leading ``-``, for example ``-date.year``.

For example:

.. code:: yaml

  blog:
    filter: '/blog/**'
    order_by: 'date'

Defines a collection named ``blog``, which contains all elements under ``/blog``, ordered by the ``date`` metadata field.

Usage
-----

Collections can be obtained from the :py:class:`~liara.site.Site` object using :py:meth:`~liara.template.SiteTemplateProxy.get_collection`. If ordered, :py:meth:`~liara.template.SiteTemplateProxy.get_next_in_collection` and :py:meth:`~liara.template.SiteTemplateProxy.get_previous_in_collection` can be used to provide next/previous links. The other use of collections are :doc:`indices`.