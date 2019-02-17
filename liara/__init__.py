import os
import pathlib
from typing import (
        Dict,
        List,
        Any,
    )
from contextlib import ContextDecorator
import multiprocessing
import itertools
import collections
from .yaml import load_yaml
from .site import Site
from .nodes import DocumentNodeFactory, RedirectionNode, ResourceNodeFactory
import logging


class SingleProcessPool(ContextDecorator):
    def map(self, f, iterable):
        return list(map(f, iterable))

    def imap_unordered(self, f, iterable):
        return list(map(f, iterable))

    def starmap(self, f, iterable):
        return [f(*p) for p in iterable]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


__version__ = '0.2.0'


def _publish(node, publisher):
    return node.publish(publisher)


def create_default_configuration() -> Dict[str, Any]:
    return {
        'content_directory': 'content',
        'resource_directory': 'resources',
        'static_directory': 'static',
        'output_directory': 'output',
        'build': {
            'clean_output': True,
            'multiprocess': True
        },
        'template': 'templates/default.yaml',
        'routes': {
            'static': 'static_routes.yaml'
        },
        'base_url': 'http://localhost:8000',
        'collections': {}
    }


def flatten_dictionary(d, sep='.', parent_key=None):
    """Flatten a nested dictionary. This uses the separator to combine keys
    together, so a dictionary access like ['a']['b'] with a separator '.' turns
    into 'a.b'."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.Mapping):
            items.extend(flatten_dictionary(v, sep=sep,
                                            parent_key=new_key).items())
        else:
            items.append((new_key, v,))
    return dict(items)


__ROOT_PATH = pathlib.PurePosixPath('/')


# Create the path from the full path as discovered during walk
# This turns something like 'directory/foo/bar' into '/foo/bar'
def _create_relative_path(path: pathlib.Path, root: pathlib.Path) \
        -> pathlib.PurePosixPath:
    # Extra check, as with_name would fail on an empty path
    if path == root:
        return __ROOT_PATH

    path = path.relative_to(root)
    return __ROOT_PATH / pathlib.PurePosixPath(path.with_name(path.stem))


class Liara:
    __site: Site = Site()
    __resource_node_factory: ResourceNodeFactory
    __document_node_factory: DocumentNodeFactory
    __redirections: List[RedirectionNode]
    __log = logging.getLogger('liara')

    def __init__(self, configuration, *, configuration_overrides={}):
        self.__redirections = []
        self.__resource_node_factory = ResourceNodeFactory()
        self.__document_node_factory = DocumentNodeFactory()

        default_configuration = create_default_configuration()
        if isinstance(configuration, str):
            project_configuration = load_yaml(open(configuration))
        else:
            project_configuration = load_yaml(configuration)
        self.__configuration = collections.ChainMap(
            # Must be flattened already
            configuration_overrides,
            flatten_dictionary(project_configuration),
            flatten_dictionary(default_configuration))

        template_configuration = pathlib.Path(self.__configuration['template'])
        self.__setup_template_backend(template_configuration)

    def __setup_template_backend(self, configuration_file: pathlib.Path):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        template_path = configuration_file.parent
        configuration = load_yaml(open(configuration_file))

        backend = configuration['backend']
        paths = configuration['paths']

        if backend == 'jinja2':
            self.__template_repository = Jinja2TemplateRepository(
                paths, template_path)
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

        routes = load_yaml(static_routes.open())
        for route in routes:
            node = RedirectionNode(
                    pathlib.PurePosixPath(route['src']),
                    pathlib.PurePosixPath(route['dst']))
            self.__redirections.append(node)
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

    def discover_content(self) -> Site:
        self.__log.info('Discovering content ...')
        configuration = self.__configuration

        content_root = pathlib.Path(configuration['content_directory'])
        self.__discover_content(self.__site, content_root)

        static_root = pathlib.Path(configuration['static_directory'])
        self.__discover_static(self.__site, static_root)

        resource_root = pathlib.Path(configuration['resource_directory'])
        self.__discover_resources(self.__site, self.__resource_node_factory,
                                  resource_root)

        static_routes = pathlib.Path(configuration['routes.static'])
        self.__discover_redirections(self.__site, static_routes)

        self.__site.create_links()

        collections = pathlib.Path(configuration['collections'])
        self.__site.create_collections(load_yaml(collections.read_text()))

        self.__log.info(f'Discovered {len(self.__site.nodes)} items')

        return self.__site

    @property
    def site(self) -> Site:
        return self.__site

    def __create_pool(self):
        if self.__configuration['build.multiprocess']:
            return multiprocessing.Pool()
        else:
            return SingleProcessPool()

    def __clean_output(self):
        import shutil
        output_directory = self.__configuration['output_directory']
        self.__log.info(f'Cleaning output directory: "{output_directory}" ...')
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)
        self.__log.info('Output directory cleaned')

    def build(self):
        from .publish import TemplatePublisher
        self.__log.info('Build started')
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        # Moving this stuff (actually, just the next command) into the with
        # statement breaks the whole process, it seems that the call is
        # skipped (only templates get populated, from the __init__ call)
        site = self.discover_content()

        for document in site.documents:
            document.validate_metadata()

        self.__log.info('Processing documents ...')
        for document in site.documents:
            document.process()
        self.__log.info(f'{len(site.documents)} processed')

        output_path = pathlib.Path(self.__configuration['output_directory'])

        publisher = TemplatePublisher(output_path, site,
                                      self.__template_repository)

        with self.__create_pool() as pool:
            self.__log.info('Publishing ...')
            pool.starmap(_publish, zip(site.documents,
                                       itertools.repeat(publisher)))
            self.__log.info(f'Published {len(site.documents)} document(s)')

            pool.starmap(_publish, zip(site.indices,
                                       itertools.repeat(publisher)))
            self.__log.info(f'Published {len(site.indices)} '
                            f'{"indices" if len(site.indices)>1 else "index"}')

            pool.starmap(_publish, zip(site.resources,
                                       itertools.repeat(publisher)))
            self.__log.info(f'Published {len(site.resources)} resource(s)')

            pool.starmap(_publish, zip(site.static,
                                       itertools.repeat(publisher)))
            self.__log.info(f'Published {len(site.static)} static file(s)')

            pool.starmap(_publish, zip(site.generated,
                                       itertools.repeat(publisher)))
            self.__log.info(f'Published {len(site.generated)} '
                            'generated file(s)')

        self.__log.info('Writing redirection file ...')
        with (output_path / '.htaccess').open('w') as output:
            for node in self.__redirections:
                output.write(f'RedirectPermanent {str(node.path)} '
                             f'{str(node.dst)}\n')
        self.__log.info(f'Wrote {len(self.__redirections)} redirections')
        self.__log.info('Build finished')

    def serve(self):
        from .server import HttpServer
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        site = self.discover_content()

        for document in site.documents:
            document.validate_metadata()

        server = HttpServer(site, self.__template_repository,
                            self.__configuration)
        server.serve()
