import cProfile
from . import Liara
from .config import create_default_configuration
from .yaml import dump_yaml
import logging
import os
import click
from .nodes import NodeKind


class Environment:
    """The command line environment.

    This provides access to global variables that are useful for command line
    commands, as well as a global liara instance."""
    __liara : Liara | None

    def __init__(self):
        self.verbose = False
        self.debug = False
        self.config = None
        self.__liara = None
        self.log = logging.getLogger('liara.cmdline')

    @property
    def liara(self) -> Liara:
        if not self.__liara:
            self.__liara = _create_liara(self.config)
        return self.__liara


pass_environment = click.make_pass_decorator(Environment, ensure=True)


def _setup_logging(*, debug: bool, verbose: bool):
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-7s %(name)s %(message)s')
        # Unfortunately PIL writes a lot of debug output, so we're disabling it
        # manually here to make debug output useful
        # This doesn't remove critical debug output -- PIL writes things like
        # PNG header data here
        logging.getLogger('PIL').setLevel(logging.INFO)
        # Markdown writes a lot of debug output as well, mostly what extensions
        # were loaded and such, which is not important for debugging
        logging.getLogger('MARKDOWN').setLevel(logging.INFO)
    elif verbose:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)-7s %(message)s')
    else:
        logging.basicConfig(
            level=logging.WARN,
            format='%(asctime)s %(levelname)-7s %(message)s')


@click.group(name='Built-in commands')
@click.option('--debug/--no-debug', default=False, help='Enable debug output.')
@click.option('--verbose', is_flag=True, help='Enable verbose output.')
@click.option('--config', default='config.yaml', type=click.Path(),
              help='Set the path to the configuration file.')
@click.option('--date', default=None, help='Override the current date.')
@click.version_option()
@pass_environment
def cli(env, debug: bool, verbose: bool, config, date: str):
    _setup_logging(debug=debug, verbose=verbose)

    if date:
        from .util import set_local_now
        import dateparser
        now = dateparser.parse(date)
        if now:
            set_local_now(now)
        else:
            env.log.error(f'Could not parse date {date}, ignoring it for this build')

    env.config = config


def main():
    from .signals import commandline_prepared

    Liara.setup_plugins()
    commandline_prepared.send(cli=cli)
    cli()


def _create_liara(config):
    if os.path.exists(config):
        return Liara(config)
    else:
        return Liara()


@cli.command()
@click.option('--profile/--no-profile')
@click.option('--profile-file', type=click.Path(writable=True),
              default='build.prof')
@click.option('--cache/--no-cache', default=True,
              help='Enable or disable the configured cache')
@click.option('--parallel/--no-parallel', default=True,
              help='Enable or disable parallel processing.')
@pass_environment
def build(env, profile, profile_file, cache: bool, parallel: bool):
    """Build a site."""
    if profile:
        pr = cProfile.Profile()
        pr.enable()
    env.liara.build(disable_cache=not cache,
                    parallel_build=parallel)
    if profile:
        pr.disable()
        pr.dump_stats(profile_file)


@cli.command()
@click.option('--type', '-t', 'link_type',
              type=click.Choice(['internal', 'external']),
              default='internal')
@pass_environment
def validate_links(env, link_type):
    """Validate links.

    Checks all internal/external links for validity. For internal links,
    a check is performed if the link target exists. For external links,
    a web request is made to the link target. If the request returns an
    error code, the link is considered invalid."""
    from .cache import MemoryCache
    from .actions import (
        validate_internal_links,
        validate_external_links,
        gather_links,
        LinkType
    )
    liara = env.liara
    site = liara.discover_content()
    cache = MemoryCache()

    env.log.debug('Processing site ...')

    for document in site.documents:
        document.process(cache)

    env.log.debug('done')

    if link_type == 'internal':
        link_type = LinkType.Internal
        env.log.debug('Checking internal links')
    elif link_type == 'external':
        link_type = LinkType.External
        env.log.debug('Checking external links')

    links = gather_links(site.documents, link_type)
    env.log.debug(f'Found {len(links)} {link_type.name.lower()} links')

    error_count = 0

    if link_type == LinkType.Internal:
        error_count = validate_internal_links(links, site)
    elif link_type == LinkType.External:
        error_count = validate_external_links(links)

    if error_count > 0:
        env.log.error(f'Found {error_count} broken links')

        return 1


@cli.command()
@pass_environment
def list_tags(env):
    """List all tags.

    This uses a metadata field named 'tags' and returns the union of all tags,
    as well as the count how often each tag is used."""
    from collections import Counter
    liara = env.liara
    site = liara.discover_content()
    tags = []
    for document in site.documents:
        tags += document.metadata.get('tags', [])

    counted_tags = sorted(Counter(tags).items(), key=lambda x: x[1],
                          reverse=True)
    for k, v in counted_tags:
        print(k, v)


@cli.command()
@click.argument('tags', nargs=-1)
@pass_environment
def find_by_tag(env, tags):
    """Find pages by tag.

    This searches the metadata for a 'tags' field, which is assumed to be
    a list of tags."""
    liara = env.liara
    site = liara.discover_content()
    tags = set(tags)
    for document in site.documents:
        for tag in document.metadata.get('tags', []):
            if tag in tags:
                print(document.src, tag)
                break


@cli.command()
@click.option('--type', '-t', 'object_type')
@pass_environment
def create(env, object_type):
    """Create a document."""
    liara = env.liara
    liara.discover_content()
    liara.create_document(object_type)


@cli.command()
@click.option('--output', '-o', type=click.File(mode='w'))
def create_config(output):
    """Create a default configuration."""
    dump_yaml(create_default_configuration(), output)


@cli.command()
@click.option('--template-backend', '-t',
              type=click.Choice(['jinja2', 'mako']),
              default='jinja2')
def quickstart(template_backend):
    """Create a quickstart project."""
    from .quickstart import generate
    generate(template_backend)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['tree', 'list']),
              default='tree')
@click.option('--type', '-t', 'content_type', multiple=True,
              type=click.Choice(
                  list(map(str.lower, NodeKind.__members__.keys()))))
@pass_environment
def list_content(env, format, content_type):
    """List all content.

    If ``format`` is set to ``tree``, this will print the content as a
    tree. If ``format`` is set to ``list``, this will produce a
    flat list instead.
    """
    import treelib
    liara = env.liara
    content = liara.discover_content()

    # We sort by path name, which makes it trivial to sort it later into a tree
    # as children always come after their parent
    nodes = sorted(content.nodes, key=lambda x: x.path)
    if not nodes:
        return

    def filter_nodes(node):
        if node.kind.name.lower() not in content_type:
            return False
        return True

    if content_type:
        nodes = list(filter(filter_nodes, nodes))

    if format == 'tree':
        tree = treelib.Tree()
        tree.create_node('Site', ('/',))
        if nodes[0].path.parts == ('/',):
            tree.create_node(f'_index ({nodes[0].kind.name})', parent=('/',),
                             data=nodes[0].path)

        known_paths = {('/',)}

        for node in nodes:
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
    elif format == 'list':
        for node in nodes:
            print(str(node.path), f'({node.kind.name})')


@cli.command()
@click.option('--browser/--no-browser',
              default=True,
              help='Open a browser window automatically')
@click.option('--port', '-p', default=8080,
              help='The port to use for the local server')
@click.option('--cache/--no-cache', default=True,
              help='Enable or disable the configured cache')
@pass_environment
def serve(env, browser, port, cache):
    """Run a local development server."""
    liara = env.liara
    liara.serve(open_browser=browser, port=port, disable_cache=not cache)


@cli.command()
@click.argument('action', type=click.Choice(['clear', 'inspect']))
@pass_environment
def cache(env, action):
    """Modify or inspect the cache."""
    import humanfriendly

    if action == 'clear':
        env.liara._get_cache().clear()
    elif action == 'inspect':
        info = env.liara._get_cache().inspect()
        size = humanfriendly.format_size(info.size, binary=True)
        print(f'Cache type:   {info.name}')
        print(f'Size:         {size}')
        print(f'Object count: {info.entry_count}')


if __name__ == '__main__':
    main()
