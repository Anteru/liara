import click
from . import BuildContext, Node, NodeKind


@click.group()
def cli():
    pass


@cli.command()
@click.argument('config', type=click.File(), default='config.yaml')
def build(config):
    """Build a site."""
    bc = BuildContext(config)
    bc.build()


@cli.command()
@click.argument('config', type=click.File(), default='config.yaml')
def list_content(config):
    """List all content."""
    import treelib
    bc = BuildContext(config)
    content = bc.discover_content()

    sorted_nodes = list(sorted(content.nodes,key=lambda x: x.path))
    tree = treelib.Tree()
    if not sorted_nodes:
        return

    tree.create_node('Site', ('/',))
    if sorted_nodes[0].path.parts == ('/',):
        tree.create_node('_index', parent=('/',), data=sorted_nodes[0])
    for node in sorted_nodes:
        path = node.path
        if len(path.parts) == 1:
            continue
        parent = tuple(path.parts[:-1])
        tree.create_node (
            f"{node.path.parts[-1]} ({node.kind.name})",
            tuple(node.path.parts), parent, node)
    tree.show(key=lambda n: str(n.data.path).casefold())