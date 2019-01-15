import click
import cProfile
from . import Liara, Node, NodeKind

pass_liara = click.make_pass_decorator(Liara)

@click.group()
@click.option('--config', default='config.yaml', metavar='PATH')
@click.version_option('0.1')
@click.pass_context
def cli(ctx, config):
    ctx.obj = Liara(config)


@cli.command()
@click.option('--profile', is_flag=True, default=False)
@pass_liara
def build(liara, profile):
    """Build a site."""
    if profile:
        pr = cProfile.Profile()
        pr.enable()
    liara.build()
    if profile:
        pr.disable()
        pr.dump_stats('build.prof')


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
    sorted_nodes = sorted(content.nodes, key=lambda x: x.path)
    if not sorted_nodes:
        return

    tree = treelib.Tree()
    tree.create_node('Site', ('/',))
    if sorted_nodes[0].path.parts == ('/',):
        tree.create_node('_index', parent=('/',), data=sorted_nodes[0].path)

    known_paths = {('/',)}

    for node in sorted_nodes:
        path = node.path
        if len(path.parts) == 1:
            continue
        parent = tuple(path.parts[:-1])

        # The following bit creates intermediate nodes for path segments
        # which are not part of the site tree. For instance, if there's a
        # static file /images/image.jpg, there won't be a /images node. In this
        # case, we create one to allow printing a full tree
        for i in range(len(parent)):
            p = tuple(parent[:i+1])
            if len(p) <= 1:
                continue
            if p not in known_paths:
                tree.create_node(f"{parent[i]}", p, parent=tuple(p[:i]),
                                 data=path)
                known_paths.add(p)

        tree.create_node(
            f"{node.path.parts[-1]} ({node.kind.name})",
            tuple(node.path.parts), parent, data=node.path)
        known_paths.add(tuple(node.path.parts))
    tree.show(key=lambda n: str(n.data).casefold())
