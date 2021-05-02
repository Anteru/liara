from blinker import signal


content_filtered = signal('content-filtered')
"""Raised when content has been removed due to a filter.

  :param liara.nodes.Node node: the node that was removed
  :param liara.site.ContentFilter filter: the filter that matched
"""

content_added = signal('content-added')
"""Raised when a content node was successfully added.

  :param liara.nodes.Node node: the node that was created
"""

commandline_prepared = signal('commandline-prepared')
"""Raised when the command line parsing environment was prepared.

  :param click.group cli: The command line group to add commands to.
"""

content_discovered = signal('content-discovered')
"""Raised after all content has been discovered.

  :param liara.site site: the site instance
"""

documents_processed = signal('documents-processed')
"""Raised after all documents have been processed. Processing includes for
instance converting the content from markdown to HTML.

  :param liara.site site: the site instance
"""

document_loaded = signal('document-loaded')
"""Raised after a document has been loaded, before any templates etc. have been
applied.

  :param liara.nodes.DocumentNode document: the document node
  :param str content: the raw document contents
"""
