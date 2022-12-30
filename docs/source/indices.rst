Indices
=======

Liara can generate indices for :any:`collections`, for instance, to create a post archive. This is a two step process -- first, a collection needs to be defined, then an index can be built on top of that collection.

Definition
----------

An index definition consists of:

- ``collection``: The name of the collection that is to be indexed.
- ``group_by``: One or more grouping statements. At least one grouping statement must be present. If the metadata is missing, an error will be raised. Use ``filter_by`` if you want to remove items which don't have certain metadata fields. Multiple fields can be specified by using a list.
- ``path``: The output path.
- ``filter_by``: Optionally filter by metadata fields. Multiple fields can be specified by using a list.
- ``create_top_level_index``: Optionally, create an index node for the top-level
  path.

For example:

.. code:: yaml

   - collection: 'blog'
     group_by: ['date.year']
     path: '/blog/archive/%1'

This snippet defines a new index which groups based on the metadata field ``date.year``, and produces paths of the form ``/blog/archive/2017`` etc. Multiple group-by fields can be used, in which case the collection will process them in turn. I.e. if grouped by year, month, first, all entries would get grouped by year, and then the entries in each separate year would get grouped by month. This requires two path components ``%1`` and ``%2`` to work, which will be consumed by each group in order.

A special syntax can be used for set-like fields, for instance tags. By adding a leading ``*``, the group gets *splatted* into separate keys. For example, a page with a metadata field ``tags`` with the value ``a, b``, grouped by ``['*tags']`` and using a path ``/tags/%1`` will be available under *both* ``/tags/a`` and ``/tags/b``.

With ``create_top_level_index``, ``/blog/archive`` will be also an index node that can be targeted by templates. Otherwise, only paths below ``/blog/archive`` will be created.

An index node will reference both pages and index nodes (for top level indices). References will strictly reference nodes created by the index.

Usage
-----

Indices can be targeted from :any:`templates`. An index node generated from an index will have the :py:attr:`~liara.template.Page.references` attribute set, which allows iterating over all referenced nodes.

Additionally, the current grouping key will be available as page metadata in the ``key`` field. In the example above, as the grouping is by ``date.year``, the key would contain the year.

For top-level indices, an additional metadata field ``top_level_index`` is created and set to ``True``. This can be used to target top level indices from templates.