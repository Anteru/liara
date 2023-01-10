Resources
=========

Liara supports resource nodes which get processed before getting placed into the output. Site-wide resources can be specified in the :doc:`configuration <../configuration>`. Per-template resources can be specified in the :doc:`template <../publish/templates>` configuration.

Currently, Liara supports the following resource types:

* `SASS <https://sass-lang.com/>`_ files
* Image thumbnails for various image formats.

Resource files get processed using resource-specific compilers.

SASS
----

SASS files (ending in ``.scss``) can be processed using either the ``sass`` command line binary or the (deprecated) ``libsass`` library. The compiler can be selected in the :ref:`configuration <sass-compiler-option>`.