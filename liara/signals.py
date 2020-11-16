from blinker import signal

# Raised when content has been discovered.
# Arguments:
# node: liara.nodes.Node - the node that was filtered
# filter: liara.site.ContentFilter - the filter that applied
content_filtered = signal('content-filtered')

# Raised when a content node was successfully added.
# Arguments:
# node: liara.nodes.Node - the node that was created
content_added = signal('content-added')

commandline_prepared = signal('commandline-prepared')