Add syntax highlighting support
===============================

Liara uses `Pygments <https://pygments.org>`_ by default for code highlighting. To make syntax look nice though, you need to include a CSS spreadsheet for your preferred style and reference that, otherwise the Pygments output will not get any styling applied.

This is a 3-step process. We'll be using the ``liara quickstart`` template here as the starting point.

1. Generate a style CSS for your preferred style. See the `Pygments documentation <https://pygments.org/docs/cmdline/#generating-styles>`_ for details, for the quick start, we'll use:

   .. code:: bash

    $ cd templates
    $ mkdir static
    $ cd static
    $ pygmentize -f html -S colorful -a .code > code.css

   .. note::
    
    This generates a CSS file for the ``colorful`` style that can be used with *all* languages.

2. Tell Liara about the CSS file and have it copied to the output. To achieve this, add ``static_directory: static`` to ``templates/default.yaml``. This will ensure the ``code.css`` file inside the ``templates/static`` repository will be copied verbatim into the output.

3. Update the CSS to reference it. Edit ``templates/page.jinja2`` and add a reference like this ``<link type="text/css" rel="stylesheet" href="/code.css" />``.

To test, add some code to one of the sample files in ``content`` using::

    ```c++
    #include <iostream>

    int main(int argc, char* argv[])
    {
        std::cout << "Hello" << std::endl;
    }
    ```
    
It should show up nicely colored in your generated output.
