Static files
============

Liara handles static files separately to minimize the amount of processing on those. Static files are symlinked to the output folder if possible. Metadata for static files can be added by using a metadata file with the same name as the static file, but the extension changed to ``.meta``. I.e. if you have an image file ``image.jpg`` and you want to provide some metadata for it, create a file ``image.meta`` (in YAML format) and place the metadata for it there.

Static files can be queried like any other node using the :py:class:`~liara.template.SiteTemplateProxy` and filtered by metadata. This can be used to create for instance gallery views.