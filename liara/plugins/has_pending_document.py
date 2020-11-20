from liara import signals


def register():
    signals.commandline_prepared.connect(_register_cli)


def _register_cli(cli):
    from liara.cmdline import pass_environment
    import sys

    @cli.command()
    @pass_environment
    def has_pending_document(env):
        """Check if there is a pending document.

        If a pending document is found, the return code from the application
        will be 1."""
        documents_filtered_by_date = 0

        def on_content_filtered(sender, **kw):
            nonlocal documents_filtered_by_date
            if kw['filter'].name == 'date':
                documents_filtered_by_date += 1

        signals.content_filtered.connect(on_content_filtered)

        env.liara.discover_content()

        if documents_filtered_by_date > 0:
            print(f'{documents_filtered_by_date} document(s) pending')
            sys.exit(1)
