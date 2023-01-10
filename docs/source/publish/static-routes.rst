Static routes
=============

Static routes provide redirections so that content is reachable under multiple URLs. The static route file is a simple YAML file with the following structure:

.. code:: yaml

  - { src: /source/path, dst: /target/path }


Each entry provides a single redirection. If static routes are configured, :py:class:`~liara.nodes.RedirectionNode` instances are created for any source URL, and additionally, an Apache 2 ``.htaccess`` redirection file gets generated. The generation of :py:class:`~liara.nodes.RedirectionNode` instances can be skipped by setting the ``server_rule_only`` flag. In that case, the ``src`` and ``dst`` path will not be normalized either, making it possible to redirect paths like ``/feed/`` (which would otherwise get normalized to ``/feed``.)