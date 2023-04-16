Shortcodes
==========

.. versionadded:: 2.5

Shortcodes allow you to call Python functions from documents before the Markdown processing starts. This can be useful if you have repeated HTML/Markdown snippets, for example, to link to a video hosting website.

Shortcodes in Liara are written as following: ``<% function-name key=value /%>``. This will result in a function call to a function registered under the name ``function-name``, passing on a dictionary ``{ 'key': 'value' }``. New functions can be registered using the :any:`liara.signals.register_markdown_shortcodes` signal, typically from a :doc:`plugin <../reference/plugins>`.

Values can be set in quotes. This is required for any value containing a space or other special characters, as the simplified syntax only supports alphanumeric characters and ``_``, ``-``. I.e. ``key=some-value`` is fine, but for a value containing spaces, you have to use quotes: ``key="some value"``. You can escape quotes inside a quoted string using ``\\"``. Newlines inside strings are preserved.

For example, you may want to create a small snippet of HTML like this:

.. code:: html

    <figure>
        <a href="/path/to/image.jpg">
            <img src="/path/to/image.thumbnail.jpg">
        </a>
        <figcaption>The caption</figcaption>
    </figure>

Instead of having to copy/paste this everywhere, you could replace this with a shortcode like this:

.. code:: markdown

    <% figure link="/path/to/image" caption="The caption" /%>

For this to work, you would register a new function:

.. code:: python

    def figure_shortcode(link, caption, **kwargs):
        return f"""<figure>
                      <a href="{link}.jpg"><img src="{link}.thumbnail.jpg"></a>
                      <figcaption>{caption}</figcaption>
                   </figure>"""

If you later decide you need to change the output, from now on you only have to change the shortcode handler, instead of having to touch all documents using it.

.. note::

    The ``**kwargs`` in the shortcode handler is not optional. Liara may pass additional context to a function using reserved parameter names.

.. note::

    User provided shortcode function names must not start with ``$`` as this is reserved for built-in functions.