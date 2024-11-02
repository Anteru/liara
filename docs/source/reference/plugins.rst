Plugins
=======

Liara supports plugins to extend the functionality. Plugins are discovered by being available in the ``liara.plugins`` namespace. For more details, see:

* https://packaging.python.org/guides/packaging-namespace-packages/
* https://packaging.python.org/guides/creating-and-discovering-plugins/#using-namespace-packages

In practice this means you can provide a plugin by placing it in the ``liara.plugins`` namespace. A plugin *must* export at least one method named ``register``, with no parameters. Here's an example of a minimal plugin:

.. code:: python

    def register():
        pass


Of course, a completely empty plugin doesn't provide any functionality. To hook into Liara, you can connect event handlers to signals. See below for more details.

Additionally, plugins can be loaded directly from a folder by specifying the ``plugin_directories`` configuration option. In this case, each ``.py`` file in that directory containing a ``register`` method will be loaded as a plugin.

Signals
-------

Liara uses signals as the extension mechanism. Signals are provided by `Blinker <https://blinker.readthedocs.io/en/stable/>`_. All signals are defined in the :py:mod:`liara.signals` module. You can think of a signal as a callback mechanism -- it calls back into the function registered to the signal (possibly multiple of them, i.e. if each plugin registers with the same signal. In that case the order of execution is undefined.)

A signal handler is a function which must accept parameters as defined in the documentation, with an extra first `sender` parameter. I.e. for :py:data:`~liara.signals.content_added`, which has one documented parameter of type :py:class:`~liara.nodes.Node`, the function signature would be:

.. code:: python

    def on_content_added(sender, node: liara.nodes.Node):
        pass

.. note::

    Signals pass parameters by name, so you must match the names in the documentation. Using ``on_content_added(sender, nd)`` for example would not work. You can however use ``**kwargs`` to capture all parameters.

The first parameter is always the sender of the signal, but is not further specified (it could be a wrapper or proxy for instance of the class you would expect to make the call), so you should always rely on the named, documented parameters.

.. note::

    Always make sure to use top-level module functions for signal handlers. Locally defined functions (i.e. within ``register()``) will get garbage collected, as signals only weakly reference the receiver.

Extending the command line
--------------------------

The command line is special as it needs to get extended at a very early stage -- before it's shown to the user for the first time. To extend the command line, you must use the :py:data:`~liara.signals.commandline_prepared` signal. liara uses `Click <https://click.palletsprojects.com/>`_ as the command line parser, but you cannot import liara's command line module directly in  your module as that would lead to circular includes. The recommendation is to put the commands directly into the registration method as following:

.. code:: python

    from liara.signals import commandline_prepared
    import click

    def register():
        commandline_prepared.connect(_register_cli)

    def _register_cli(sender, cli):
        from liara.cmdline import pass_environment

        @cli.command()
        @pass_environment
        def my_new_command(env):
            print(env.liara)

Note the use of ``@pass_environment``. This requests Click to pass the Liara command line environment as the first parameter, which contains the Liara instance. See :py:class:`~liara.cmdline.Environment` for more details.

Caching & plugins
-----------------

When using plugins, Liara's caching mechanism may fail to rebuild content if a plugin changes. Generally speaking, when updating a plugin, clear the cache using ``liara cache clear`` before building again.