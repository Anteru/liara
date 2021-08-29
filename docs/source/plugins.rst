Plugins
=======

Liara supports plugins to extend the functionality. Plugins are discovered by being available in the ``liara.plugins`` namespace. For more details, see:

* https://packaging.python.org/guides/packaging-namespace-packages/
* https://packaging.python.org/guides/creating-and-discovering-plugins/#using-namespace-packages

In practice this means you can provide a plugin by placing it in the ``liara.plugins`` namespace. A plugin *must* export at least one method named ``register``, with no parameters. Here's an example of a minimal plugin:

.. code:: python

    def register():
        pass


Of course, a completely empty plugin doesn't provide any functionality. To hook into Liara, you can connect event handlers to signals. The signals are defined in the :py:mod:`liara.signals` module.

Extending the command line
--------------------------

The command line is special as it needs to get extended at a very early stage -- before it's shown to the user for the first time. To extend the command line, you must use the :py:data:`~liara.signals.commandline_prepared` signal. liara uses `Click <https://click.palletsprojects.com/>`_ as the command line parser, but you cannot import liara's command line module directly in  your module as that would lead to circular includes. The recommendation is to put the commands directly into the registration method as following:

.. code:: python

    from liara.signals import commandline_prepared
    import click

    def register():
        commandline_prepared.connect(_register_cli)

    def _register_cli(cli):
        from liara.cmdline import pass_environment

        @cli.command()
        @pass_environment
        def my_new_command(env):
            print(env.liara)

Note the use of ``@pass_environment``. This requests Click to pass the Liara command line environment as the first parameter, which contains the Liara instance. See :py:class:`~liara.cmdline.Environment` for more details.