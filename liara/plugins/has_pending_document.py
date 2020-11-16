from liara import signals
from liara.cmdline import Command


class HasPendingDocuments(Command):
    def configure(self, parser):
        return parser.add_parser(
            'has-pending-document',
            help='Check if the site has pending document. '
                 'If yes, the exit code will be 1.')

    def execute(self, liara, options):
        """Return 1 if there is at least one document which was date filtered."""
        documents_filtered_by_date = 0

        def on_content_filtered(sender, **kw):
            nonlocal documents_filtered_by_date
            if kw['filter'].name == 'date':
                documents_filtered_by_date += 1

        signals.content_filtered.connect(on_content_filtered)

        liara.discover_content()

        if documents_filtered_by_date > 0:
            print(f'{documents_filtered_by_date} document(s) pending')
            return 1


def _on_commandline_prepared(sender, command_registry):
    command_registry.append(HasPendingDocuments())


def register():
    signals.commandline_prepared.connect(_on_commandline_prepared)