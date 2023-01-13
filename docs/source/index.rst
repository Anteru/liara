.. Liara documentation master file, created by
   sphinx-quickstart on Fri Feb 22 19:32:55 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Liara's documentation!
=================================

Liara is a static page generator, written in `Python <https://python.org>`_. It creates web sites which can be deployed to any web server and require no server-side logic. Liara is ideally suited for blogs or personal pages, especially if you need good syntax highlighting.

Getting started with Liara is easy: Everything is configured through a small set of text files, and the output can be customized using templates. See :doc:`quickstart` for a short introduction.

Liara is also very fast -- it can process sites with hundreds of pages and images within seconds. Where possible, Liara will not copy files, making it particularly suitable for sites having large amounts of binary data (videos, executables, etc.) Finally, Liara is also extensible using :doc:`reference/plugins` allowing you to add new functionality to tailor it for your particular use case.

.. toctree::
   :maxdepth: 1
   :caption: Documentation

   quickstart
   changelog/index
   configuration

   content/index
   publish/index
   reference/index
