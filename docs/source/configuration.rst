Configuration
=============

.. _configuration:

liara is driven through configuration files. The main file is ``config.yaml``, which can reference other configuration files. To get the full default configuration, use :option:`create-config` command line option.

Directory settings
------------------

* ``content_directory``: The root directory for all content. Output paths will be build relative to this folder.
* ``resource_directory``: The folder containing resources, i.e. ``SASS`` or other files that need to get processed before they can be written to the output.
* ``static_directory``: The folder containing static files, for instance downloads, images, videos etc.
* ``output_directory``: The output directory.

Build settings
--------------

* ``build.clean_output``: If set to ``True``, the output directory will be deleted on every build.
* ``build.cache_directory``: The directoy where the cache will be stored.

Content settings
----------------

* ``content.filters``: Filters that will be applied while discovering content.
* ``template``: The :any:`template <templates>` definition to apply to the content.
* ``collections``: Points to the file containing the :any:`collection <collections>` definitions.
* ``feeds``: Points to the file containing the feed definitions.
* ``indices``: Points to the file containing the :doc:`index definitions <indices>`.
* ``metadata``: Points to the file containing the :doc:`site metadata <metadata>`.
* ``relaxed_date_parsing``: If enabled, metadata fields named ``date`` will be processed twice. By default, liara assumes that ``date`` contains a markup-specific date field. If this option is on, and the ``date`` field is pointing at a string, liara will try to parse that string into a timestamp.
* ``allow_relative_links``: Allow the usage of relative links in content files. This has a negative build time impact on any file containing relative links and is thus recommended to be left off.

Other settings
--------------

* ``routes.static``: Points to the file containing :any:`static routes <static-routes>`.