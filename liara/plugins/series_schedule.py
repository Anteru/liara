from liara import signals
import click

def register():
    signals.commandline_prepared.connect(_register_cli)


def _register_cli(cli):
    from liara.cmdline import pass_environment
    import sys

    @cli.command()
    @click.argument('series')
    @click.option('--day-only', default=False)
    @pass_environment
    def show_series_schedule(env, series, day_only):
        """Show the schedule for a series. A series is defined by adding a
        metadata entry "series" to a document."""
        documents_in_series = []

        def on_content_added(sender, node):
            if node.metadata.get('series') == series:
                documents_in_series.append(node)

        signals.content_added.connect(on_content_added)

        env.liara.discover_content()

        known_dates = set()

        for document in sorted(documents_in_series, key=lambda x: (x.metadata['date'], x.metadata['title'],)):
            date_format = '%x' if day_only else '%x %X'
            date = document.metadata['date']
            if date in known_dates:
                print ('* ', end='')
            known_dates.add(date)
            print(document.metadata['date'].strftime(date_format),
                document.metadata['title'])

        sys.exit(0)
