Indices
=======

Liara can generate indices for :any:`collections`, for instance, to create a post archive. This is a two step process -- first, a collection needs to be defined, then an index can be built on top of that collection.

Definition
----------

An index definition consists of:

- The name of the collection that is to be indexed.
- One or more grouping statements.
- The output path.

For example:

.. code:: yaml

   - collection: 'blog'
     group_by: ['date.year']
     path: '/blog/archive/%1'

This snippet defines a new index which groups based on the metadata field ``date.year``, and produces paths of the form ``/blog/archive/2017`` etc. Multiple group-by fields can be used, in which case the collection will process them in turn. I.e. if grouped by year, month, first, all entries would get grouped by year, and then the entries in each separate year would get grouped by month. This requires two path components ``%1`` and ``%2`` to work, which will be consumed by each group in order.

A special syntax can be used for set-like fields, for instance tags. By adding a leading ``*``, the group gets *splatted* into separate keys. For example, a page with a metadata field ``tags`` with the value ``a, b``, grouped by ``['*tags']`` and using a path ``/tags/%1`` will be available under *both* ``/tags/a`` and ``/tags/b``.

Usage
-----

Indices can be targeted from :any:`templates`. An index node generated from an index will have the :py:attr:`~liara.template.Page.references` attribute set, which allows iterating over all referenced nodes.