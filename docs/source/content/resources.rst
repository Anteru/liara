Resources
=========

Liara supports resource nodes which get processed before getting placed into the output. Site-wide resources can be specified in the :doc:`configuration <../configuration>`. Per-template resources can be specified in the :doc:`template <../publish/templates>` configuration. There are two kind of resource nodes:

* Explicit: In this case, the input file will not get published to the output. For example, ``.sass`` files should not be published.
* Implicit: In this case, both the source file and the generated resource node is published. For example, for images, the original image is published along thumbnails.

The resource folder should only contain *explicit* resources.

Currently, Liara supports the following resource types:

* `SASS <https://sass-lang.com/>`_ files
* Image thumbnails for various image formats.

.. note::

    Image thumbnails are *implicit* resource nodes. There's no need to place images into the resource folder to get thumbnails generated.

SASS
----

SASS files (ending in ``.scss``) can be processed using either the ``sass`` command line binary or the (deprecated) ``libsass`` library. The compiler can be selected in the :ref:`configuration <sass-compiler-option>`.