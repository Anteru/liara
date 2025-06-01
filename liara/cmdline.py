import cProfile
from . import Liara
from .config import create_default_configuration
from .yaml import dump_yaml
import logging
import os
import click
from .nodes import NodeKind
from typing import Literal, IO, Callable, Optional, Union
from .site import Site
from .nodes import Node, NodeKind, _parse_node_kind
import pathlib
from .cache import MemoryCache

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
        assert self.__liara is not None
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
def cli(env: Environment, debug: bool, verbose: bool, config, date: str):
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


def _create_liara(config, *, overrides=None):
    if os.path.exists(config):
        return Liara(config, configuration_overrides=overrides)
    else:
        return Liara(configuration_overrides=overrides)


@cli.command()
@click.option('--profile/--no-profile')
@click.option('--profile-file', type=click.Path(writable=True),
              default='build.prof')
@click.option('--cache/--no-cache', default=True,
              help='Enable or disable the configured cache')
@click.option('--parallel/--no-parallel', default=True,
              help='Enable or disable parallel processing.')
@pass_environment
def build(env: Environment, profile: bool,
          profile_file: str | bytes | os.PathLike,
          cache: bool, parallel: bool):
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
def validate_links(env: Environment, link_type: Literal['internal', 'external']):
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
    args = {
        '$data': site.merged_data
    }
    for document in site.documents:   
        document.process(cache, **args)

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
def list_tags(env: Environment):
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
def find_by_tag(env: Environment, tags: list[str]):
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
def create(env: Environment, object_type: str):
    """Create a document."""
    liara = env.liara
    liara.discover_content()
    liara.create_document(object_type)


@cli.command()
@click.option('--output', '-o', type=click.File(mode='w'))
def create_config(output: IO):
    """Create a default configuration."""
    dump_yaml(create_default_configuration(), output)


@cli.command()
@click.option('--template-backend', '-t',
              type=click.Choice(['jinja2', 'mako']),
              default='jinja2')
def quickstart(template_backend: Literal['jinja2', 'mako']):
    """Create a quickstart project."""
    from .quickstart import generate
    generate(template_backend)


class _Node:
    """Helper class for tree printing, as the liara site node tree doesn't
    contain intermediate nodes."""
    def __init__(self, name: str, data=None):
        self.__name = name
        self.__children = []
        self.__data = data

    def add_child(self, node: "_Node"):
        self.__children.append(node)

    @property
    def children(self) -> list["_Node"]:
        return self.__children

    @property
    def name(self):
        return self.__name
    
    @property
    def data(self):
        return self.__data


def _print_tree(node: _Node, get_label: Callable[[_Node], str], prefix='', last=True):
    """Pretty-print a fully populated tree (meaning: all intermediate nodes
    are present.)"""
    empty = "    "
    last_branch = "└── "
    continue_traversal = "│   "
    branch = "├── "
    
    if node.name == 'Site':
        # Special case the root node: Don't add a prefix here
        print('Site')
        if node.children:
            for i, c in enumerate(sorted(node.children, key=lambda n: n.name)):
                _print_tree(c, get_label, '', i == (len(node.children) - 1))
    else:
        # Normal node - print the prefix so far, append the right branch
        # symbol, then the label
        print(prefix + (last_branch if last else branch) + get_label(node))
        if node.children:
            for i, c in enumerate(sorted(node.children, key=lambda n: n.name)):
                _print_tree(c, get_label, 
                            # Logic here is: If we're last we're not adding
                            # a vertical bar, just spaces
                            prefix + (empty if last else continue_traversal),
                            i == (len(node.children) - 1))


@cli.command()
@click.option('--format', '-f', type=click.Choice(['tree', 'list', 'json']),
              default='tree')
@click.option('--type', '-t', 'content_type', multiple=True,
              type=click.Choice(
                  list(map(str.lower, NodeKind.__members__.keys()))))
@pass_environment
def list_content(env: Environment,
                 format: Literal['tree', 'list', 'json'],
                 content_type: list[str]):
    """List all content.

    If ``format`` is set to ``tree``, this will print the content as a
    tree. If ``format`` is set to ``list``, this will produce a
    flat list instead. JSON will print a JSON structure with information for
    each node.
    """
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

    def get_node_label(node):
        label = f"{node.path.parts[-1]}"
        if node.kind == NodeKind.Resource:
            label += f"(Resource, generated from '{node.src}')"
        else:
            label +=  f"({node.kind.name})"
        
        return label

    if format == 'tree':
        root = _Node('Site')
        node_map = {'/': root}

        def add_or_create(path, data=None):
            if str(path) in node_map:
                return

            # Create parent nodes recursively, as needed
            add_or_create(path.parent)
            
            n = _Node(path.name, data)
            node_map[str(path.parent)].add_child(n)
            node_map[str(path)] = n
        
        for node in nodes:
            path = node.path

            add_or_create(path, node)

        import sys
        # This seems to be required to get UTF-8 output redirection to work
        # in powershell. Unclear why
        sys.stdout.reconfigure(encoding='utf-8')

        def get_label(node):
            if node.data:
                return get_node_label(node.data)
            return node.name

        _print_tree(root, get_label)
    elif format == 'list':
        for node in nodes:
            print(str(node.path), get_node_label(node))
    elif format == 'json':
        import json
        result = {
            'version': 1,
            'nodes': []
        }
        for node in nodes:
            data = {
                'path': str(node.path),
                'kind': node.kind.name
            }
            if node.src:
                data['source'] = str(node.src)

            result['nodes'].append(data)
        print(json.dumps(result, indent=4))


@cli.command()
@click.option('--browser/--no-browser',
              default=True,
              help='Open a browser window automatically')
@click.option('--port', '-p', default=8080,
              help='The port to use for the local server')
@click.option('--cache/--no-cache', default=True,
              help='Enable or disable the configured cache')
@pass_environment
def serve(env: Environment, browser: bool, port: int, cache: bool):
    """Run a local development server."""
    import watchfiles
    from .server import HttpServer
    # We run two threads here, one for file watching which recreates either
    # liara or the site, and one to run the server in

    liara = _create_liara(env.config)
    server = HttpServer(open_browser=browser, port=port)

    liara._set_base_url_override(server.get_url())

    server.start(liara, MemoryCache())

    try:
        # We need this nested loop in case the cache or output directory
        # changes. The server can actually cope with this, but we need to
        # ignore those folders
        while True:
            config = liara._get_configuration()
            output_directory = config["output_directory"]
            ignore_dirs = [output_directory]

            match config["build.cache.type"]:
                case "fs":
                    ignore_dirs.append(config["build.cache.fs.directory"])
                case "db":
                    ignore_dirs.append(config["build.cache.db.directory"])

            watch_filter = watchfiles.DefaultFilter(ignore_dirs=ignore_dirs)
            
            for change in watchfiles.watch('.',
                                        watch_filter=watch_filter,
                                        recursive=True):
                # TODO We can optimize this by skipping  the reconfigure
                # if it's a _known_ content node that changes
                liara = _create_liara(env.config)
                liara._set_base_url_override(server.get_url())

                server.reconfigure(liara, MemoryCache())
                break
    except KeyboardInterrupt:
        pass

    server.stop()


@cli.command()
@click.argument('action', type=click.Choice(['clear', 'inspect']))
@pass_environment
def cache(env: Environment, action: Literal['clear', 'inspect']):
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

@cli.group()
def inspect():
    """Inspect state, for example, site data or template matching."""
    pass

@inspect.command('data')
@pass_environment
def inspect_data(env: Environment, list_files: bool):
    """Inspect the content of `site.data`."""
    import pprint
    liara = env.liara
    liara.discover_content()

    # Using dict() here improves formatting, as pprint starts with
    # mappingproxy(...) otherwise which is an implementation detail
    pprint.pprint(dict(liara.site.merged_data))

@inspect.command('list-data-files')
@pass_environment
def inspect_data_files(env: Environment):
    """List all data files."""
    liara = env.liara
    liara.discover_content()

    for df in liara.site.data:
        print(df.src)

class _SiteShim(Site):
    """Helper class to inject fake nodes for `template-match` so
    we can match selectors with `?kind=` specified."""
    def __init__(self, site: Site):
        self.__site = site
        self.__fakes = {}

    def register_fake_node(self, path: str, kind: NodeKind):
        self.__fakes[pathlib.PurePosixPath(path)] = kind

    def get_node(self, path: Union[str, pathlib.PurePosixPath]) \
            -> Optional[Node]:
        if path in self.__fakes:
            assert isinstance(path, pathlib.PurePosixPath)
            n = Node()
            n.path = path
            match self.__fakes[path]:
                case NodeKind.Document:
                    n.kind = NodeKind.Document
                case NodeKind.Index:
                    n.kind = NodeKind.Index

            return n
                    
        return self.__site.get_node(path)

@inspect.command('template-match')
@click.argument('path')
@click.option('--kind', type=click.Choice(['document', 'index']),
              help='Override or set the node kind at the specified path.')
@pass_environment
def inspect_template_match(env: Environment, path: str, kind: Optional[Literal['document', 'index']]):
    """Match a template pattern."""
    liara = env.liara
    liara.discover_content()

    if not path.startswith('/'):
        path = '/' + path

    site_shim = _SiteShim(liara.site)
    if kind is not None:
        site_shim.register_fake_node(path, _parse_node_kind(kind))
    else:
        if (node := liara.site.get_node(path)) is None:
            site_shim.register_fake_node(path, NodeKind.Document)
        else:
            print(f'Node "{path}" exists with kind: {node.kind.name}')

    template_repository = liara._get_template_repository()
    match, pattern = template_repository._match_template(pathlib.PurePosixPath(path), site_shim)
    print(f'Using template "{match}" for path "{path}" due to pattern "{pattern}"')


if __name__ == '__main__':
    main()
