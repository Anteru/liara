import datetime
import logging
import os
import pathlib
import time
import multiprocessing
from dataclasses import dataclass

from typing import (
    Any,
    Callable,
    IO,
    ChainMap,
    List,
    Dict,
    Optional,
    Text,
    Union,
    )
from types import MappingProxyType

import collections

from liara.template import TemplateRepository

from . import config, signals
from .site import Site, ContentFilterFactory
from .nodes import (
    DocumentNodeFactory,
    RedirectionNode,
    ResourceNodeFactory,

    _process_node_sync
)

from .cache import Cache, FilesystemCache, NullCache, Sqlite3Cache, RedisCache
from .tools import SassCompiler
from .util import (
    CaseInsensitiveDictionary,
    FilesystemWalker,

    flatten_dictionary,
    file_digest,
    get_hash_key_for_map
)
from .yaml import load_yaml

__version__ = '2.7.3'
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


@dataclass
class _LoadedModule:
    module: object
    hash: bytes


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


def _process_resource_task(t):
    return t.process()


def _setup_multiprocessing_worker(log_level):
    from .cmdline import _setup_logging
    if log_level == logging.DEBUG:
        _setup_logging(debug=True, verbose=False)
    elif log_level == logging.INFO:
        _setup_logging(debug=False, verbose=True)
    else:
        _setup_logging(debug=False, verbose=False)


@dataclass
class CompressionResult:
    output_path: pathlib.Path
    input_size: int
    output_size: int
    format: str


def _compress_helper(path: pathlib.Path,
                     method: Callable[[bytes], bytes],
                     suffix: str,
                     format: str):
    output_path = path.with_suffix(path.suffix + suffix)

    input_data = path.open('rb').read()
    compressed = method(input_data)
    output_path.open('wb').write(compressed)

    return CompressionResult(output_path, len(input_data), len(compressed),
                             format)


def _zstd_compress(path: pathlib.Path):
    try:
        import compression.zstd
        return _compress_helper(path, compression.zstd.compress, '.zst', 'Zstd')
    except ImportError:
        import zstd
        return _compress_helper(path, zstd.compress, '.zst', 'Zstd')


def _gz_compress(path: pathlib.Path):
    import gzip
    return _compress_helper(path, gzip.compress, '.gz', 'GZip')


def _brotli_compress(path: pathlib.Path):
    import brotli
    return _compress_helper(path, brotli.compress, '.br', 'Brotli')


_COMPRESSION_FORMATS = CaseInsensitiveDictionary({
    'Zstd': _zstd_compress,
    'GZip': _gz_compress,
    'Brotli': _brotli_compress
})


class Compressor:
    def __init__(self, configuration: Dict[str, List[str]]):
        # The configuration is a mapping from file extensions to compressors to
        # use
        from collections import defaultdict
        self.__map = defaultdict(list)
        for key, value in configuration.items():
            # Remove leading dot if any
            key = key.lstrip('.')

            for e in value:
                self.__map[key].append(_COMPRESSION_FORMATS[e])

    def compress(self, path: pathlib.Path):
        # Match path against the extensions
        result: List[CompressionResult] = []
        assert path is not None
        ext = path.suffix.lstrip('.')
        if compressors := self.__map.get(ext):
            for compressor in compressors:
                result.append(compressor(path))

        return result


def _compress(path: pathlib.Path, compressor: Compressor):
    return compressor.compress(path)


class Liara:
    """Main entry point for Liara. This class handles all the state required
    to process and build a site."""
    __site: Site
    __resource_node_factory: ResourceNodeFactory
    __document_node_factory: DocumentNodeFactory
    __redirections: List[Dict[str, str]]
    __log = logging.getLogger('liara')
    __cache: Cache
    # When running using 'serve', this will be set to the local URL
    __base_url_override: Optional[str] = None
    __registered_plugins: Dict[object, _LoadedModule] = dict()
    __filesystem_walker: FilesystemWalker
    __template_repository: TemplateRepository

    def __init__(self,
                 configuration: Optional[
                     Union[str, IO, IO[bytes], IO[Text]]] = None,
                 *,
                 configuration_overrides: Optional[Dict] = None):
        self.__site = Site()
        self.__redirections = []

        if configuration_overrides is None:
            configuration_overrides = {}

        default_configuration = config.create_default_configuration()
        if configuration is None:
            project_configuration = {}
        elif isinstance(configuration, str):
            # If it's a string, we treat it as a filename and open the
            # corresponding file
            project_configuration = load_yaml(open(configuration, 'rb'))
        else:
            # Some kind of IO stream
            project_configuration = load_yaml(configuration)

        # It's none if the YAML file is empty, for instance, when creating a
        # new site from scratch. In this case, set it to an empty dict as
        # flatten_dictionary cannot handle None
        if project_configuration is None:
            project_configuration = dict()

        ignore_list = {
            'content.markdown.extensions',
            'content.markdown.config',
            'content.markdown.output',
            'build.compression'
        }

        self.__configuration = collections.ChainMap(
            # Must be flattened already
            configuration_overrides,
            flatten_dictionary(project_configuration, ignore_keys=ignore_list),
            flatten_dictionary(default_configuration, ignore_keys=ignore_list))

        Liara.setup_plugins()

        plugin_directories = self.__configuration['plugin_directories']
        if isinstance(plugin_directories, str):
            plugin_directories = [plugin_directories]

        for directory in plugin_directories:
            self._load_plugins(directory)

        self.__resource_node_factory = ResourceNodeFactory(
            self.__configuration
        )
        self.__document_node_factory = DocumentNodeFactory(
            self.__configuration
        )

        # Must come before the template backend, as that can look for files
        self.__filesystem_walker = FilesystemWalker(
            self.__configuration['ignore_files'])

        # Must come before the template backend, as those can use caches
        self.__setup_cache()

        template_configuration = pathlib.Path(self.__configuration['template'])
        self.__setup_template_backend(template_configuration)

        self.__setup_content_filters(self.__configuration['content.filters'])

    @classmethod
    def setup_plugins(cls) -> None:
        import liara.plugins
        import pkgutil
        import importlib
        import inspect

        def iter_namespace(ns_pkg):
            return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")

        plugins = {
            name: importlib.import_module(name)
            for _, name, _ in iter_namespace(liara.plugins)
        }

        for name, module in plugins.items():
            if name in cls.__registered_plugins:
                continue

            cls.__log.debug(f'Initializing plugin: {name}')
            assert hasattr(module, 'register')
            module.register()
            cls.__registered_plugins[name] = _LoadedModule(
                module,
                file_digest(open(inspect.getfile(module), 'rb')))

    def __setup_cache(self) -> None:
        # Deprecated since version 2.2
        cache_directory = self.__configuration.get('build.cache_directory')
        if cache_directory:
            self.__log.warning(
                "'build.cache_directory' is deprecated. Please "
                "use 'build.cache.<cache_type>.directory' instead.")
            cache_directory = pathlib.Path(cache_directory)

        # Deprecated since version 2.2
        cache_type = self.__configuration.get('build.cache_type')
        if cache_type:
            self.__log.warning(
                "'build.cache_type' is deprecated. Please use "
                "'build.cache.type' instead.")

        # Official value since 2.2
        if cache_type is None:
            # We need to check first because this is part of the default
            # config and it would overwrite the user setting if they were using
            # the deprecated value
            cache_type = self.__configuration.get('build.cache.type')

        match cache_type:
            case 'db':
                self.__log.debug('Using Sqlite3Cache')
                dir = self.__configuration.get('build.cache.db.directory')
                if dir and cache_directory is None:
                    cache_directory = pathlib.Path(dir)
                assert cache_directory
                self.__cache = Sqlite3Cache(cache_directory)
            case 'fs':
                self.__log.debug('Using FilesystemCache')
                dir = self.__configuration.get('build.cache.fs.directory')
                if dir and cache_directory is None:
                    cache_directory = pathlib.Path(dir)
                assert cache_directory
                self.__cache = FilesystemCache(cache_directory)
            case 'redis':
                self.__log.debug('Using RedisCache')
                self.__cache = RedisCache(
                    self.__configuration['build.cache.redis.host'],
                    self.__configuration['build.cache.redis.port'],
                    self.__configuration['build.cache.redis.db'],
                    datetime.timedelta(minutes=self.__configuration[
                        'build.cache.redis.expiration_time'])
                )
            case 'none':
                self.__cache = NullCache()
                self.__log.debug('Not using any cache')
            case _:
                self.__log.warning('No cache backend configured')

    def __setup_content_filters(self, filters: List[str]) -> None:
        content_filter_factory = ContentFilterFactory()
        for f in filters:
            self.__site.register_content_filter(
                content_filter_factory.create_filter(f)
            )

    def __setup_template_backend(self, configuration_file: pathlib.Path):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        template_path = configuration_file.parent
        default_configuration = config.create_default_template_configuration()
        configuration = load_yaml(configuration_file.open('rb'))

        ignore_list = {
            # Legacy
            'image_thumbnail_sizes',
            'image_thumbnail_formats',
            # Since 2.4.1
            'image_thumbnails',

            'backend_options',
            'paths'
        }

        configuration = ChainMap(
            flatten_dictionary(configuration, ignore_keys=ignore_list),
            flatten_dictionary(default_configuration, ignore_keys=ignore_list))

        backend = configuration['backend']
        paths = configuration['paths']

        # Legacy option
        if 'image_thumbnail_sizes' in configuration:
            # Deprecated since 2.4.1
            self.__log.warning(
                "'image_thumbnail_sizes' is deprecated. Please use "
                "'image_thumbnails.sizes' instead.")
            self.__thumbnail_definition = {
                'sizes': configuration.get('image_thumbnail_sizes', {}),
                'formats': ['original']
            }
        else:
            self.__thumbnail_definition = configuration.get(
                'image_thumbnails',
                {
                    'sizes': {},
                    'formats': ['original']
                })

        if backend == 'jinja2':
            self.__template_repository = Jinja2TemplateRepository(
                paths, template_path, self.__cache,
                options=configuration['backend_options']['jinja2'])
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
        if not static_routes.exists():
            return

        base_url = site.metadata['base_url']

        routes = load_yaml(static_routes.open('rb'))
        for route in routes:
            node = RedirectionNode(
                    pathlib.PurePosixPath(route['src']),
                    pathlib.PurePosixPath(route['dst']),
                    base_url=base_url)
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

        for dirpath, filenames in self.__filesystem_walker.walk(content_root):
            directory = pathlib.Path(dirpath)
            # Need to run two passes here: First, we check if an _index file is
            # present in this folder, in which case it's the root of this
            # directory
            # Otherwise, we create a new index node
            node: Node
            indexNode: Optional[Node] = None
            for filename in filenames:
                if filename.startswith('_index'):
                    src = pathlib.Path(os.path.join(dirpath, filename))
                    if src.suffix not in document_factory.known_types:
                        supported_file_types = ', '.join(
                            document_factory.known_types
                        )
                        self.__log.warning(
                            f'Ignoring "{src}", unsupported file '
                            'type for index node. Supported file '
                            f'types are: {supported_file_types}.')
                        continue

                    relative_path = _create_relative_path(directory,
                                                          content_root)

                    metadata_path = src.with_suffix('.meta')
                    if metadata_path.exists():
                        node = document_factory.create_node(src.suffix, src,
                                                            relative_path,
                                                            metadata_path)
                    else:
                        node = document_factory.create_node(src.suffix, src,
                                                            relative_path)

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

                if filename.endswith('.meta'):
                    # Metadata files are handled while dealing with the actual
                    # content
                    continue

                src = pathlib.Path(os.path.join(directory, filename))
                path = _create_relative_path(src, content_root)

                if src.suffix in document_factory.known_types:
                    metadata_path = src.with_suffix('.meta')
                    try:
                        if metadata_path.exists():
                            node = document_factory.create_node(src.suffix,
                                                                src,
                                                                path,
                                                                metadata_path)
                        else:
                            node = document_factory.create_node(src.suffix,
                                                                src,
                                                                path)
                    except Exception as e:
                        self.__log.warning(
                            f'Failed to load "{src}". Skipping file.',
                            exc_info=e)
                        continue

                    site.add_document(node)
                    # If there's an index node, we add each document directly
                    # below it manually to the reference list
                    # This way, a simply query using index.references returns
                    # all documents, instead of having to go through the
                    # children and filter by type
                    if indexNode:
                        assert isinstance(indexNode, IndexNode)
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
        for dirpath, filenames in self.__filesystem_walker.walk(static_root):
            directory = pathlib.Path(dirpath)

            for filename in filenames:
                src = directory / filename

                path = _create_relative_path(src, static_root)
                # We need to re-append the source suffix
                # We can't use .with_suffix, as this will break on paths like
                # a.b.c, where with_suffix('foo') will produce a.b.foo instead
                # of a.b.c.foo
                path = path.parent / (path.name + src.suffix)

                # We don't support metadata on static content inside the
                # static directory. Everything here gets passed through
                # unchanged, as we can't tell a .meta file apart from an
                # actual static file
                node = StaticNode(src, path)
                site.add_static(node)

    def __discover_resources(self, site: Site,
                             resource_factory: ResourceNodeFactory,
                             resource_root: pathlib.Path) -> None:
        for dirpath, filenames in self.__filesystem_walker.walk(resource_root):
            for filename in filenames:
                if filename.endswith('.meta'):
                    continue

                src = pathlib.Path(os.path.join(dirpath, filename))
                path = _create_relative_path(src, resource_root)

                if src.suffix not in resource_factory.known_types:
                    supported_resource_types = ','.join(
                        resource_factory.known_types)
                    self.__log.warning(
                        f'Ignoring resource "{src}" as the file '
                        f'type {src.suffix} is not a supported '
                        'resource file type. Supported resource types are: '
                        + supported_resource_types + '. '
                        'Please place static files that don\'t '
                        'require resource processing into the '
                        'static directory.')
                    continue

                metadata_path = src.with_suffix('.meta')
                if metadata_path.exists():
                    node = resource_factory.create_node(src.suffix, src, path,
                                                        metadata_path)
                else:
                    node = resource_factory.create_node(src.suffix, src, path)
                site.add_resource(node)

    def __discover_feeds(self, site: Site,
                         feed_definition: pathlib.Path) -> None:
        from .feeds import JsonFeedNode, RSSFeedNode, SitemapXmlFeedNode

        if not feed_definition.exists():
            return

        for key, options in load_yaml(feed_definition.open('rb')).items():
            path = pathlib.PurePosixPath(options['path'])
            del options['path']

            match key:
                case 'rss':
                    site.add_generated(RSSFeedNode(path, site, **options))
                case 'json':
                    site.add_generated(JsonFeedNode(path, site, **options))
                case 'sitemap':
                    site.add_generated(SitemapXmlFeedNode(path, site,
                                                          **options))
                case _:
                    self.__log.warning(f'Unknown feed type: "{key}", ignored')

    def __discover_metadata(self, site: Site, metadata: pathlib.Path) -> None:
        if not metadata.exists():
            return

        site.set_metadata(load_yaml(metadata.open('rb')))

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
                    load_yaml(collections.open('rb')))

        if 'indices' in configuration:
            indices = pathlib.Path(configuration['indices'])
            if indices.exists():
                self.__site.create_indices(
                    load_yaml(indices.open('rb')))

        self.__site.create_links()

        self.__log.info(f'Discovered {len(self.__site.nodes)} items')

        signals.content_discovered.send(self, site=self.__site)

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

    def __build_resources(self, site: Site, cache: Cache,
                          parallel_build=True):
        self.__log.info('Processing resources ...')

        if parallel_build:
            async_resource_tasks = []
            async_resource_results = []

            for resource in site.resources:
                if async_task := resource.process(cache):
                    async_resource_tasks.append((resource, async_task,))

            self.__log.debug('%d async resource tasks pending ...',
                             len(async_resource_tasks))

            with multiprocessing.Pool(
                    initializer=_setup_multiprocessing_worker,
                    initargs=(logging.root.level,)) as pool:
                async_resource_results = pool.map(
                    _process_resource_task,
                    [r[1] for r in async_resource_tasks])

            self.__log.debug('Processed %d async resource tasks',
                             len(async_resource_tasks))

            for ((resource, task), result) in zip(async_resource_tasks,
                                                  async_resource_results):
                resource.content = result
                task.update_cache(result, cache)
        else:
            for resource in site.resources:
                _process_node_sync(resource, cache)

        self.__log.info(f'Processed {len(site.resources)} resources')

    def __set_cache_prefix(self):
        """Set the cache prefix based on anything that could impact the
        site generation that is not the content of the file that is processed.

        We currently use the configuration, site metadata (as this is affected
        for example by the 'base_url' when locally serving), data nodes,
        and plugin hashes of loaded plugins."""
        import hashlib
        site_data = dict()
        for data_node in self.__site.data:
            site_data.update(data_node.content)

        plugin_hashes = {
            key: value.hash for key, value in self.__registered_plugins.items()
        }

        self.__cache.set_key_prefix(
            hashlib.shake_128(
                get_hash_key_for_map(self.__configuration)
                + get_hash_key_for_map(self.__site.metadata)
                + get_hash_key_for_map(site_data)
                + get_hash_key_for_map(plugin_hashes)
                + __version__.encode('utf-8')).digest(16)
        )

    def check_tools(self, try_install=False):
        """Check for requested tools and optionally try to install them."""
        sass_compiler = self.__configuration['build.resource.sass.compiler']
        if sass_compiler == 'cli':
            scss = SassCompiler()
            if not scss.is_present():
                if try_install:
                    if scss.try_install():
                        self.__log.info('Installed `sass` compiler')
                    else:
                        self.__log.error('Failed to install `sass` compiler')
                        return False
                else:
                    self.__log.error('Could not find `sass` compiler.')
                    return False
            else:
                self.__log.info('Found working `sass` compiler')

        return True

    def build(self, discover_content=True, *, disable_cache=False,
              parallel_build=True):
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

        self.__set_cache_prefix()

        self.__log.info('Processing documents ...')
        cache = self.__cache if not disable_cache else NullCache()
        self.__log.debug(f'Using {cache.__class__.__name__} for caching')
        for document in site.documents:
            try:
                args = {
                    '$data': site.merged_data
                }
                _process_node_sync(document, cache, **args)
            except Exception as e:
                self.__log.warning('Failed to process document "%s". Document '
                                   'content will be empty.',
                                   document.src,
                                   exc_info=e)
        self.__log.info(f'Processed {len(site.documents)} documents')
        signals.documents_processed.send(self, site=self.__site)

        self.__build_resources(site, cache, parallel_build)

        output_path = pathlib.Path(self.__configuration['output_directory'])

        publisher = TemplatePublisher(output_path, site,
                                      self.__template_repository)

        published_files = []

        self.__log.info('Publishing ...')
        for document in site.documents:
            published_files.append(document.publish(publisher))
        self.__log.info(f'Published {len(site.documents)} document(s)')

        for index in site.indices:
            published_files.append(index.publish(publisher))
        self.__log.info(f'Published {len(site.indices)} '
                        f'{"indices" if len(site.indices) > 1 else "index"}')

        for resource in site.resources:
            published_files.append(resource.publish(publisher))
        self.__log.info(f'Published {len(site.resources)} resource(s)')

        for static in site.static:
            published_files.append(static.publish(publisher))
        self.__log.info('Published %d static file(s)', len(site.static))

        if site.generated:
            for generated in site.generated:
                generated.generate()
                published_files.append(generated.publish(publisher))
            self.__log.info(f'Published {len(site.generated)} '
                            'generated file(s)')

        if self.__redirections:
            self.__log.info('Writing redirection file ...')
            with (output_path / '.htaccess').open('w') as output:
                output.write('RewriteEngine on\n')
                for node in self.__redirections:
                    output.write(f'RedirectPermanent {node["src"]} '
                                 f'{node["dst"]}\n')
            self.__log.info(f'Wrote {len(self.__redirections)} redirections')

        published_files = list(filter(None, published_files))

        signals.content_published.send(self, files=published_files)

        if 'build.compression' in self.__configuration:
            import humanfriendly as hf

            self.__log.info(f'Compression enabled, processing '
                            f'{len(published_files)} file(s)')
            compressor = Compressor(self.__configuration['build.compression'])
            compression_result: List[CompressionResult] = []
            if parallel_build:
                with multiprocessing.Pool() as pool:
                    for result_list in pool.starmap(
                            _compress,
                            [(f, compressor,) for f in published_files]):
                        compression_result += result_list
            else:
                for published_file in published_files:
                    compression_result += compressor.compress(published_file)

            self.__log.info('Finished compressing')

            for format in _COMPRESSION_FORMATS.keys():
                filtered = list(filter(lambda x: x.format == format,
                                       compression_result))

                if not filtered:
                    self.__log.info(f'  - No files compressed for format {format}')
                    continue

                uncompressed_size = sum([cr.input_size for cr in filtered])
                compressed_size = sum([cr.output_size for cr in filtered])
                self.__log.info(
                    f'  - Compression using {format}: '
                    f'{len(filtered)} compressed files, '
                    f'{hf.format_size(uncompressed_size, binary=True)}'
                    f' -> {hf.format_size(compressed_size, binary=True)}, '
                    f'{hf.round_number(compressed_size / uncompressed_size * 100)}%')

        end_time = time.time()
        self.__log.info(f'Build finished ({end_time - start_time:.2f} sec)')
        self.__cache.persist()

    def create_document(self, t):
        """Create a new document using a generator."""
        source_path = pathlib.Path(
            self.__configuration['generator_directory']) / (t + '.py')
        module = self._load_module(source_path, t)
        assert hasattr(module, 'generate')
        # We just checked it has this attribute
        path = module.generate(self.__site, self.__configuration)  # type: ignore
        self.__log.info(f'Generated "{path}"')

    def _load_plugins(self, folder):
        plugin_path = pathlib.Path(folder)
        for plugin in plugin_path.rglob('*.py'):
            module = self._load_module(plugin)
            if hasattr(module, 'register'):
                # We just checked it has 'register', so there's no need to warn
                # us here
                module.register()  # type: ignore
                # Keep it around to prevent garbage collection
                self.__registered_plugins[plugin] = _LoadedModule(
                    module,
                    file_digest(plugin.open('rb')))

    def _load_module(self, path, name=''):
        import importlib.util
        self.__log.debug(f'Initializing plugin from module: "{path}"')
        # Prevent modules from being loaded twice
        if module := self.__registered_plugins.get(path):
            self.__log.debug(f'Module "{path}" already registered, skipping')
            return module.module

        if not name:
            name = path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec
        assert spec.loader

        module = importlib.util.module_from_spec(spec)
        assert module

        spec.loader.exec_module(module)
        return module

    def _get_cache(self) -> Cache:
        """Debug/internal access to the cache for inspection."""
        return self.__cache

    def _get_template_repository(self) -> TemplateRepository:
        """Debug/internal access to the template repository for inspection."""
        return self.__template_repository

    def _get_configuration(self) -> MappingProxyType[str, Any]:
        """Debug/internal access to the configuration for inspection."""
        return MappingProxyType(self.__configuration)

    def _set_base_url_override(self, url: str):
        """Internal use only"""
        self.__base_url_override = url
