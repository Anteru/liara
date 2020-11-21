from blinker import signal


content_filtered = signal('content-filtered')
"""Raised when content has been discovered.

  :param liara.nodes.Node node: the node that was filtered
  :param liara.site.ContentFilter filter: the filter that applied
"""

content_added = signal('content-added')
"""Raised when a content node was successfully added.

  :param liara.nodes.Node node: the node that was created
"""

commandline_prepared = signal('commandline-prepared')
"""Raised when the command line parsing environment was prepared.

  :param click.group cli: The command line group to add commands to.
"""
