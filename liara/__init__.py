import os
import pathlib
import logging
import time

from typing import (
        List,
        Callable,
        Set,
        Dict
    )

import collections

from . import config, signals
from .site import Site, ContentFilterFactory
from .nodes import (
    DocumentNodeFactory,
    RedirectionNode,
    ResourceNodeFactory,
)

from .cache import Cache, FilesystemCache, Sqlite3Cache
from .util import flatten_dictionary
from .yaml import load_yaml

__version__ = '2.1.3'
__all__ = [
    'actions',
    'cache',
    'cmdline',
    'config',
    'feeds',
    'md',
    'nodes',
    'publish',
    'query',
    'quickstart',
    'server',
    'site',
    'template',
    'util',
    'yaml'
]

# Required to allow plugins to participate
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

# We cache it here as it's used a lot during _create_relative_path and shows up
# in profiles otherwise
__ROOT_PATH = pathlib.PurePosixPath('/')


def _create_relative_path(path: pathlib.Path, root: pathlib.Path) \
        -> pathlib.PurePosixPath:
    """"Make a root-relative path.

    This turns `directory/foo/bar` into `/foo/bar`. Both `root` and `path`
    can be relative or absolute paths."""
    # Extra check, as with_name would fail on an empty path
    if path == root:
        return __ROOT_PATH

    path = path.relative_to(root)
    return __ROOT_PATH / pathlib.PurePosixPath(path.with_name(path.stem))


class Liara:
    """Main entry point for Liara. This class handles all the state required
    to process and build a site."""
    __site: Site
    __resource_node_factory: ResourceNodeFactory
    __document_node_factory: DocumentNodeFactory
    __redirections: List[RedirectionNode]
    __log = logging.getLogger('liara')
    __cache: Cache
    __document_post_processors: List[Callable]
    # When running using 'serve', this will be set to the local URL
    __base_url_override: str = None
    __registered_plugins: Set[str] = set()

    def __init__(self, configuration=None, *, configuration_overrides={}):
        self.__site = Site()
        self.__redirections = []

        default_configuration = config.create_default_configuration()
        if configuration is None:
            project_configuration = {}
        elif isinstance(configuration, str):
            project_configuration = load_yaml(open(configuration))
        else:
            project_configuration = load_yaml(configuration)

        # It's none of the YAML file is empty, for instance, when creating a
        # new site from scratch. In this case, set it to an empty dict as
        # flatten_dictionary cannot handle None
        if project_configuration is None:
            project_configuration = dict()

        self.__configuration = collections.ChainMap(
            # Must be flattened already
            configuration_overrides,
            flatten_dictionary(project_configuration),
            flatten_dictionary(default_configuration))

        Liara.setup_plugins()

        self.__resource_node_factory = ResourceNodeFactory()
        self.__document_node_factory = DocumentNodeFactory(
            self.__configuration
        )

        # Must come before the template backend, as those can use caches
        cache_directory = pathlib.Path(
            self.__configuration['build.cache_directory'])
        if self.__configuration['build.cache_type'] == 'db':
            self.__log.debug('Using Sqlite3Cache')
            self.__cache = Sqlite3Cache(cache_directory)
        elif self.__configuration['build.cache_type'] == 'fs':
            self.__log.debug('Using FilesystemCache')
            self.__cache = FilesystemCache(cache_directory)

        template_configuration = pathlib.Path(self.__configuration['template'])
        self.__setup_template_backend(template_configuration)

        self.__setup_content_filters(self.__configuration['content.filters'])

    @classmethod
    def setup_plugins(self) -> None:
        import liara.plugins
        import pkgutil, importlib

        def iter_namespace(ns_pkg):
            return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")
            
        plugins = {
            name: importlib.import_module(name)
            for _, name, _ in iter_namespace(liara.plugins)
        }

        for name, module in plugins.items():
            if name  in self.__registered_plugins:
                continue
            
            self.__log.debug(f'Initializing plugin: {name}')
            module.register()
            self.__registered_plugins.add(name)

    def __setup_content_filters(self, filters: List[str]) -> None:
        content_filter_factory = ContentFilterFactory()
        for f in filters:
            self.__site.register_content_filter(
                content_filter_factory.create_filter(f)
            )

    def __setup_template_backend(self, configuration_file: pathlib.Path):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        template_path = configuration_file.parent
        configuration = load_yaml(open(configuration_file))

        backend = configuration['backend']
        paths = configuration['paths']

        self.__thumbnail_definition = configuration.get(
            'image_thumbnail_sizes', {})

        if backend == 'jinja2':
            self.__template_repository = Jinja2TemplateRepository(
                paths, template_path, self.__cache)
        elif backend == 'mako':
            self.__template_repository = MakoTemplateRepository(
                paths, template_path)
        else:
            raise Exception(f'Unknown template backend: "{backend}"')

        if 'resource_directory' in configuration:
            resource_directory = pathlib.Path(
                configuration['resource_directory'])

            self.__discover_resources(self.__site,
                                      self.__resource_node_factory,
                                      template_path / resource_directory)

        if 'static_directory' in configuration:
            static_directory = pathlib.Path(
                configuration['static_directory'])
            self.__discover_static(self.__site,
                                   template_path / static_directory)

    def __discover_redirections(self, site: Site, static_routes: pathlib.Path):
        from .nodes import RedirectionNode
        if not static_routes.exists():
            return

        base_url = site.metadata['base_url']

        routes = load_yaml(static_routes.open())
        for route in routes:
            node = RedirectionNode(
                    pathlib.PurePosixPath(route['src']),
                    pathlib.PurePosixPath(route['dst']),
                    base_url = base_url)
            if route.get('server_rule_only', False):
                self.__redirections.append({
                    'src': route['src'],
                    'dst': base_url + route['dst']
                })
            else:
                self.__redirections.append({
                    'src': str(node.path),
                    'dst': base_url + str(node.dst)
                })
                site.add_generated(node)

    def __discover_content(self, site: Site, content_root: pathlib.Path) \
            -> None:
        from .nodes import DataNode, IndexNode, Node, StaticNode

        document_factory = self.__document_node_factory

        for (dirpath, _, filenames) in os.walk(content_root):
            directory = pathlib.Path(dirpath)
            # Need to run two passes here: First, we check if an _index file is
            # present in this folder, in which case it's the root of this
            # directory
            # Otherwise, we create a new index node
            node: Node
            indexNode: Node = None
            for filename in filenames:
                if filename.startswith('_index'):
                    src = pathlib.Path(os.path.join(dirpath, filename))
                    relative_path = _create_relative_path(directory,
                                                          content_root)
                    node = document_factory.create_node(src.suffix,
                                                        src, relative_path)
                    site.add_document(node)
                    break
            else:
                node = IndexNode(_create_relative_path(directory,
                                                       content_root))
                site.add_index(node)
                indexNode = node

            for filename in filenames:
                if filename.startswith('_index'):
                    continue

                src = pathlib.Path(os.path.join(directory, filename))
                path = _create_relative_path(src, content_root)

                if src.suffix in document_factory.known_types:
                    node = document_factory.create_node(src.suffix, src, path)
                    site.add_document(node)
                    # If there's an index node, we add each document directly
                    # below it manually to the reference list
                    # This way, a simply query using index.references returns
                    # all documents, instead of having to go through the
                    # children and filter by type
                    if indexNode:
                        indexNode.add_reference(node)
                elif src.suffix in {'.yaml'}:
                    node = DataNode(src, path)
                    site.add_data(node)
                else:
                    metadata_path = src.with_suffix('.meta')
                    path = path.with_suffix(''.join(src.suffixes))
                    if metadata_path.exists():
                        node = StaticNode(src, path, metadata_path)
                    else:
                        node = StaticNode(src, path)
                    site.add_static(node)

    def __discover_static(self, site: Site, static_root: pathlib.Path) -> None:
        from .nodes import StaticNode
        for dirpath, _, filenames in os.walk(static_root):
            directory = pathlib.Path(dirpath)

            for filename in filenames:
                src = directory / filename
                path = _create_relative_path(src, static_root)
                # We need to re-append the source suffix
                # We can't use .with_suffix, as this will break on paths like
                # a.b.c, where with_suffix('foo') will produce a.b.foo instead
                # of a.b.c.foo
                path = path.parent / (path.name + src.suffix)

                metadata_path = src.with_suffix('.meta')
                if metadata_path.exists():
                    node = StaticNode(src, path, metadata_path)
                else:
                    node = StaticNode(src, path)
                site.add_static(node)

    def __discover_resources(self, site: Site,
                             resource_factory: ResourceNodeFactory,
                             resource_root: pathlib.Path) -> None:
        for dirpath, _, filenames in os.walk(resource_root):
            for filename in filenames:
                src = pathlib.Path(os.path.join(dirpath, filename))
                path = _create_relative_path(src, resource_root)

                metadata_path = src.with_suffix('.meta')
                if metadata_path.exists():
                    node = resource_factory.create_node(src.suffix, src, path,
                                                        metadata_path)
                else:
                    node = resource_factory.create_node(src.suffix, src, path)
                site.add_resource(node)

    def __discover_feeds(self, site: Site, feeds: pathlib.Path) -> None:
        from .feeds import JsonFeedNode, RSSFeedNode, SitemapXmlFeedNode

        if not feeds.exists():
            return

        for key, options in load_yaml(feeds.open()).items():
            path = pathlib.PurePosixPath(options['path'])
            del options['path']

            if key == 'rss':
                feed = RSSFeedNode(path, site, **options)
                site.add_generated(feed)
            elif key == 'json':
                feed = JsonFeedNode(path, site, **options)
                site.add_generated(feed)
            elif key == 'sitemap':
                feed = SitemapXmlFeedNode(path, site, **options)
                site.add_generated(feed)
            else:
                self.__log.warn(f'Unknown feed type: "{key}", ignored')

    def __discover_metadata(self, site: Site, metadata: pathlib.Path) -> None:
        if not metadata.exists():
            return

        site.set_metadata(load_yaml(metadata.open()))

        if self.__base_url_override:
            site.set_metadata_item('base_url', self.__base_url_override)

    def discover_content(self) -> Site:
        """Discover all content and build the :py:class:`liara.site.Site`
        instance."""
        self.__log.info('Discovering content ...')
        configuration = self.__configuration

        metadata = pathlib.Path(configuration['metadata'])
        self.__discover_metadata(self.__site, metadata)

        content_root = pathlib.Path(configuration['content_directory'])
        self.__discover_content(self.__site, content_root)

        static_root = pathlib.Path(configuration['static_directory'])
        self.__discover_static(self.__site, static_root)

        resource_root = pathlib.Path(configuration['resource_directory'])
        self.__discover_resources(self.__site, self.__resource_node_factory,
                                  resource_root)

        static_routes = pathlib.Path(configuration['routes.static'])
        self.__discover_redirections(self.__site, static_routes)

        # Feeds use metadata, so this must come after self.__discover_metadata
        feeds = pathlib.Path(configuration['feeds'])
        self.__discover_feeds(self.__site, feeds)

        if self.__thumbnail_definition:
            self.__site.create_thumbnails(self.__thumbnail_definition)

        self.__site.create_links()

        if 'collections' in configuration:
            collections = pathlib.Path(configuration['collections'])
            if collections.exists():
                self.__site.create_collections(
                    load_yaml(collections.read_text()))

        if 'indices' in configuration:
            indices = pathlib.Path(configuration['indices'])
            if indices.exists():
                self.__site.create_indices(
                    load_yaml(indices.read_text()))

        self.__site.create_links()

        self.__log.info(f'Discovered {len(self.__site.nodes)} items')

        signals.content_discovered.send(self, site = self.__site)

        return self.__site

    @property
    def site(self) -> Site:
        return self.__site

    def __clean_output(self):
        import shutil
        output_directory = self.__configuration['output_directory']
        self.__log.info(f'Cleaning output directory: "{output_directory}" ...')
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)
        self.__log.info('Output directory cleaned')

    def build(self, discover_content=True):
        """Build the site.

        :param bool discover_content: If `True`, :py:meth:`discover_content`
                                      will be called first.
        """
        from .publish import TemplatePublisher
        self.__log.info('Build started')
        start_time = time.time()
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        if discover_content:
            site = self.discover_content()
        else:
            site = self.__site

        for document in site.documents:
            document.validate_metadata()

        self.__log.info('Processing documents ...')
        for document in site.documents:
            document.process(self.__cache)
        self.__log.info(f'Processed {len(site.documents)} documents')
        signals.documents_processed.send(self, site = self.__site)

        self.__log.info('Processing resources ...')
        for resource in site.resources:
            resource.process(self.__cache)
        self.__log.info(f'Processed {len(site.resources)} resources')

        output_path = pathlib.Path(self.__configuration['output_directory'])

        publisher = TemplatePublisher(output_path, site,
                                      self.__template_repository)

        self.__log.info('Publishing ...')
        for document in site.documents:
            document.publish(publisher)
        self.__log.info(f'Published {len(site.documents)} document(s)')

        for index in site.indices:
            index.publish(publisher)
        self.__log.info(f'Published {len(site.indices)} '
                        f'{"indices" if len(site.indices)>1 else "index"}')

        for resource in site.resources:
            resource.publish(publisher)
        self.__log.info(f'Published {len(site.resources)} resource(s)')

        for static in site.static:
            static.publish(publisher)
        self.__log.info(f'Published {len(site.static)} static file(s)')

        if site.generated:
            for generated in site.generated:
                generated.generate()
                generated.publish(publisher)
            self.__log.info(f'Published {len(site.generated)} '
                            'generated file(s)')

        if self.__redirections:
            self.__log.info('Writing redirection file ...')
            with (output_path / '.htaccess').open('w') as output:
                base_url = site.metadata['base_url']
                output.write('RewriteEngine on\n')
                for node in self.__redirections:
                    output.write(f'RedirectPermanent {node["src"]} '
                                 f'{node["dst"]}\n')
            self.__log.info(f'Wrote {len(self.__redirections)} redirections')

        end_time = time.time()
        self.__log.info(f'Build finished ({end_time - start_time:.2f} sec)')
        self.__cache.persist()

    def serve(self, *, open_browser=True):
        """Serve the current site using a local webserver."""
        from .server import HttpServer
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        self.__base_url_override = HttpServer.get_url()
        
        site = self.discover_content()
        
        server = HttpServer(site, self.__template_repository,
                            self.__configuration,
                            open_browser=open_browser)

        for document in site.documents:
            document.validate_metadata()

        server.serve()

    def create_document(self, t):
        """Create a new document using a generator."""
        import importlib

        source_path = os.path.join(self.__configuration['generator_directory'],
                                   t + '.py')
        spec = importlib.util.spec_from_file_location(t, source_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        path = module.generate(self.__site, self.__configuration)
        self.__log.info(f'Generated "{path}"')
