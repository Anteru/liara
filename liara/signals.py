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
