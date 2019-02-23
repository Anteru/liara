import argparse
import cProfile
from . import Liara, create_default_configuration, __version__
from .yaml import dump_yaml
import logging
import os


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(title='Commands',
                                       metavar='COMMAND',
                                       help='The command to invoke')

    build_cmd = subparsers.add_parser('build', help='Build the site')
    build_cmd.add_argument('--profile', action='store_true')
    build_cmd.add_argument('--profile-file', default='build.prof')
    build_cmd.set_defaults(func=build)

    validate_links_cmd = subparsers.add_parser('validate-links',
                                               help='Validate links')
    validate_links_cmd.set_defaults(func=validate_links)

    find_by_tag_cmd = subparsers.add_parser('find-by-tag',
                                            help='Find content by tag')
    find_by_tag_cmd.add_argument('tag', nargs='+')
    find_by_tag_cmd.set_defaults(func=find_by_tag)

    serve_cmd = subparsers.add_parser('serve', help='Start a web server')
    serve_cmd.set_defaults(func=serve)

    quickstart_cmd = subparsers.add_parser('quickstart',
                                           help='Generate a quickstart blog')
    quickstart_cmd.set_defaults(func=quickstart)

    create_config_cmd = subparsers.add_parser('create-config',
                                              help='Create a default '
                                                   'configuration')
    create_config_cmd.add_argument('-o', '--output', default='config.yaml')
    create_config_cmd.set_defaults(func=create_config)

    list_tags_cmd = subparsers.add_parser('list-tags',
                                          help='List all unique entries in the'
                                               ' metadata.tags field.')
    list_tags_cmd.set_defaults(func=list_tags)

    list_content_cmd = subparsers.add_parser('list-content',
                                             help='Show all tracked content')
    list_content_cmd.add_argument('-f', '--format', choices=['tree', 'list'],
                                  default='tree')
    list_content_cmd.set_defaults(func=list_content)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(name)s %(message)s')
    else:
        logging.basicConfig(level=logging.WARN,
                            format='%(asctime)s %(name)s %(message)s')

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


def _create_liara(options):
    if os.path.exists(options.config):
        return Liara(options.config)
    else:
        return Liara()


def build(options):
    """Build a site."""
    if options.profile:
        pr = cProfile.Profile()
        pr.enable()
    liara = _create_liara(options)
    liara.build()
    if options.profile:
        pr.disable()
        pr.dump_stats(options.profile_file)


def validate_links(options):
    """Validate links."""
    from .cache import MemoryCache
    from .actions import validate_document_links
    liara = _create_liara(options)
    site = liara.discover_content()
    cache = MemoryCache()

    for document in site.documents:
        document.process(cache)
        validate_document_links(document, site)


def list_tags(options):
    """List all tags.

    This uses a metadata field named 'tags' and returns the union of all tags,
    as well as the count how often each tag is used."""
    from collections import Counter
    liara = _create_liara(options)
    site = liara.discover_content()
    tags = []
    for document in site.documents:
        tags += document.metadata.get('tags', [])

    counted_tags = sorted(Counter(tags).items(), key=lambda x: x[1],
                          reverse=True)
    for k, v in counted_tags:
        print(k, v)


def find_by_tag(options):
    """Find pages by tag.

    This searches the metadata for a 'tags' field, which is assumed to be
    a list of tags."""
    liara = _create_liara(options)
    site = liara.discover_content()
    tags = set(options.tag)
    for document in site.documents:
        for tag in document.metadata.get('tags', []):
            if tag in tags:
                print(document.src, tag)
                break


def create_config(options):
    """Create a default configuration."""
    dump_yaml(create_default_configuration(), options.output)


def quickstart(options):
    """Create a quickstart project."""
    from .quickstart import generate
    generate()


def list_content(options):
    """List all content."""
    import treelib
    liara = _create_liara(options)
    content = liara.discover_content()

    # We sort by path name, which makes it trivial to sort it later into a tree
    # as children always come after their parent
    sorted_nodes = sorted(content.nodes, key=lambda x: x.path)
    if not sorted_nodes:
        return

    if options.format == 'tree':
        tree = treelib.Tree()
        tree.create_node('Site', ('/',))
        if sorted_nodes[0].path.parts == ('/',):
            tree.create_node('_index', parent=('/',),
                             data=sorted_nodes[0].path)

        known_paths = {('/',)}

        for node in sorted_nodes:
            path = node.path
            if len(path.parts) == 1:
                continue
            parent = tuple(path.parts[:-1])

            # The following bit creates intermediate nodes for path segments
            # which are not part of the site tree. For instance, if there's a
            # static file /images/image.jpg, there won't be a /images node. In
            # this case, we create one to allow printing a full tree
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
    elif options.format == 'list':
        for node in sorted_nodes:
            print(str(node.path))


def serve(options):
    """Run a local development server."""
    liara = _create_liara(options)
    liara.serve()
