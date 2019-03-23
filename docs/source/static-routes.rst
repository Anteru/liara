Static routes
=============

Static routes provide redirections so that content is reachable under multiple URLs. If static routes are configured, :py:class:`~liara.nodes.RedirectionNode` instances are created for any source URL, and additionally, an Apache 2 ``.htaccess`` redirection file gets generated.