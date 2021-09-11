Content
=======

No site would be complete without content. In Liara, content is provided in a separate directory, and mirrored into the output. That is, a document placed in ``content-root/foo/bar.md`` will be routed to ``/foo/bar/index.html``. The content root can be set in the :doc:`configuration`.

Documents
---------

The bulk of the content are document nodes -- Markdown or Html files which get processed by Liara to Html and which get templates applied. Liara supports some common Markdown extensions to handle tables and code snippets.

Metadata
--------

Every document in Liara must have metadata associated with it, which contains at least the document title. There are two ways to add metadata to a document: Embedding it inside the document or by using a separate ``.meta`` file.

.. note::

   Metadata has to be either embedded or placed in a ``.meta`` file, but not both. If a ``.meta`` file is found the whole document content will be used and no search for metadata within it will be performed.

When embedding it inside the document, the metadata must be placed at the beginning of the file. The metadata can be provided as YAML or TOML. For YAML, use ``---`` as the delimiter, for TOML, use ``+++``. Documents can be empty as long as the metadata is present, so this is a valid document with YAML metadata:

.. code:: yaml

   ---
   title: " This is an example"
   ---

You cannot mix the delimiters, i.e. using ``---`` to start and ``+++`` to end will result in a failure. Using more characters is also not supported.

Alternatively, the metadata can be stored in a ``.meta`` file next to the document. The ``.meta`` file **must** contain YAML.

.. note::

   The ``.meta`` file name must be the same as the original file name, with the last suffix changed to ``.meta``. For instance, if your content is stored in ``blog-post.md``, the metadata file would be ``blog-post.meta``. If you have a file with multiple suffixes like ``blog-post.new.md``, then the metadata file has to be named ``blog-post.new.meta``.

Content filters
---------------

.. _content-filters:

Some metadata fields in Liara are processed by a :py:class:`~liara.site.ContentFilter`: ``date`` and ``status``. ``date`` expects a timestamp, for example:

.. code:: yaml

   ---
   title: "My blog post"
   date: 2096-11-22 19:30:56+01:00
   ---

Documents with a date that lies in the future relative to the time the build is invoked will get filtered by the :py:class:`~liara.site.DateFilter`. ``status`` can be used to hide content by setting it to ``private`` -- which in turn will make the :py:class:`~liara.site.StatusFilter` filter out the page. The filters can be set up in the :doc:`configuration`.
