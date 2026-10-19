Enable live-reload
==================

To enable live reloading while using ``liara serve``, add this to your template code for the main page (for example, just before the closing ``</body>`` tag):

For Jinja2, use:

.. code:: html+jinja

    {{ build_context.live_reload_code }}

For Mako, use:

.. code:: mako

    ${build_context.live_reload_code}

This will inject a snippet of live-reload JavaScript which will auto-reload the page whenever the content changes and a rebuild is triggered. When using ``liara build``, it will evaluate to an empty string, so it's safe to leave it in.
