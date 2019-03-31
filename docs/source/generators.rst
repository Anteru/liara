Generators
==========

Generators are used to create documents from the command line. Typically, they simplify the creation of metadata fields like ``date``. To create a generator, you need to write some Python code. Place a new file into the generator directory (see :doc:`configuration`), which has the same name as the document type you want to create. For instance, if you want to use ``liara create blog-post``, you'd create a file named ``blog-post.py``. This file must export a single function ``generate(site: Site, configuration: Dict[Any, str]) -> pathlib.Path``. Invoking ``liara create <type>`` will first build the site, and then call the ``generate`` script to produce a new document. The function *must* return the location it stored the document to.

.. warning::

   Generator scripts can execute arbitrary Python code. Be careful when using untrusted code.