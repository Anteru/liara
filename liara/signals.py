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

  :param liara.site.Site site: the site instance
"""

documents_processed = signal('documents-processed')
"""Raised after all documents have been processed.

  :param liara.site.Site site: the site instance

  Processing includes the conversion from Markdown to HTML.
"""

document_loaded = signal('document-loaded')
"""Raised after a document has been loaded.

  :param liara.nodes.DocumentNode document: the document node
  :param str content: the raw document contents

  This signal is raised after loading, but before processing starts. Templates
  etc. have thus not been applied to the document yet.
"""
