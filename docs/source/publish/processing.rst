Processing order
================

Liara processes the content in multiple stages.

* Plugins are loaded and the command line is configured.
* The content is discovered. As part of the content discovery, collections and indices get generated as well.
* All documents are processed (i.e. Markdown is converted to HTML, etc.)
* All resources are processed
* The content is published (this is where templates get applied)
* Additional output files get created (redirections, etc.)