import click
from . import Liara, Node, NodeKind

pass_liara = click.make_pass_decorator(Liara)

@click.group()
@click.option('--config', default='config.yaml', metavar='PATH')
@click.version_option('0.1')
@click.pass_context
def cli(ctx, config):
    ctx.obj = Liara(config)


@cli.command()
@pass_liara
def build(liara):
    """Build a site."""
    liara.build()


@cli.command()
@pass_liara
def validate_links(liara):
    site = liara.discover_content()
    for document in site.documents:
        document.process_content()
        document.validate_links(site)


@cli.command()
@pass_liara
def list_content(liara):
    """List all content."""
    import treelib
    content = liara.discover_content()

    # We sort by path name, which makes it trivial to sort it later into a tree
    # as children always come after their parent
    sorted_nodes = sorted(content.nodes,key=lambda x: x.path)
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