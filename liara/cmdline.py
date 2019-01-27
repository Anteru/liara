import click
import cProfile
from . import Liara, create_default_configuration, dump_yaml, __version__

pass_liara = click.make_pass_decorator(Liara)


@click.group()
@click.option('--config', default='config.yaml', metavar='PATH')
@click.version_option(__version__)
@click.pass_context
def cli(ctx, config):
    ctx.obj = Liara(config)


@cli.command()
@click.option('--profile', is_flag=True, default=False)
@click.option('--profile-file', default='build.prof')
@pass_liara
def build(liara, profile, profile_file):
    """Build a site."""
    if profile:
        pr = cProfile.Profile()
        pr.enable()
    liara.build()
    if profile:
        pr.disable()
        pr.dump_stats(profile_file)


@cli.command()
@pass_liara
def validate_links(liara):
    """Validate links."""
    site = liara.discover_content()
    for document in site.documents:
        document.process_content()
        document.validate_links(site)


@cli.command()
@pass_liara
def list_tags(liara):
    """List all tags.

    This uses a metadata field named 'tags' and returns the union of all tags,
    as well as the count how often each tag is used."""
    from collections import Counter
    site = liara.discover_content()
    tags = []
    for document in site.documents:
        tags += document.metadata.get('tags', [])

    counted_tags = sorted(Counter(tags).items(), key=lambda x: x[1],
                          reverse=True)
    for k, v in counted_tags:
        print(k, v)


@cli.command()
@click.argument('tag', nargs=-1)
@pass_liara
def find_by_tag(liara, tag):
    """Find pages by tag.

    This searches the metadata for a 'tags' field, which is assumed to be
    a list of tags."""
    site = liara.discover_content()
    tags = set(tag)
    for document in site.documents:
        for tag in document.metadata.get('tags', []):
            if tag in tags:
                print(document.src, tag)
                break


@cli.command()
@click.argument('output', type=click.File('w'))
def create_config(output):
    """Create a default configuration."""
    dump_yaml(create_default_configuration(), output)


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
