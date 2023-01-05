from .nodes import (
    DocumentNode,
    GeneratedNode,
    IndexNode,
    NodeKind,
    ResourceNode,
    StaticNode
)
import pathlib
from .site import Site
from .template import TemplateRepository
from .publish import TemplatePublisher
from .cache import Cache
import sys
import logging
import webbrowser
import mimetypes


class HttpServer:
    __log = logging.getLogger('liara.HttpServer')

    def get_url(self):
        return f'http://127.0.0.1:{self.__port}'

    def __init__(self, *, open_browser=True, port=8080):
        self.__open_browser = open_browser
        self.__port = port

    def _reload_template_paths(self):
        """Reload the template configuration.

        This ensures that any change to the template configuration is
        reflected in the template repository."""
        from .yaml import load_yaml
        template_configuration = pathlib.Path(self.__configuration['template'])
        configuration = load_yaml(template_configuration.open())
        self.__template_repository.update_paths(configuration['paths'])

    def _build_single_node(self, path: pathlib.PurePosixPath):
        """Build a single node.

        Build a single node on-demand. Special rules apply to make sure this is
        useful for actual work -- for instance, document/resource nodes
        are always rebuilt from scratch, and for documents, we also reload
        all templates."""
        from collections import namedtuple
        BuildResult = namedtuple('BuildResult', ['path', 'cache'])
        node = self.__site.get_node(path)

        if node is None:
            self.__log.warning(f'Could not find node for path: "{path}"')
            return (None, None,)

        # We always regenerate the content
        if node.kind in {NodeKind.Document, NodeKind.Resource}:
            assert isinstance(node, DocumentNode) \
                   or isinstance(node, ResourceNode)
            node.reload()
            if async_task := node.process(self.__cache):
                node.content = async_task.process()
                async_task.update_cache(node.content, self.__cache)
            cache = False
        elif node.kind in {NodeKind.Generated}:
            assert isinstance(node, GeneratedNode)
            node.generate()
            cache = False
        # We don't cache index nodes so templates get re-applied
        elif node.kind == NodeKind.Index:
            cache = False
        else:
            cache = True

        if node.kind == NodeKind.Document:
            self._reload_template_paths()

        assert isinstance(node, StaticNode) \
               or isinstance(node, DocumentNode) \
               or isinstance(node, GeneratedNode) \
               or isinstance(node, IndexNode) \
               or isinstance(node, ResourceNode)

        return BuildResult(node.publish(self.__publisher), cache)

    def serve(self, site: Site, template_repository: TemplateRepository,
              configuration, cache: Cache):
        """Serve the site with just-in-time processing.

        This does not build the whole site up-front, but rather builds nodes
        on demand. Nodes requiring templates are rebuilt from scratch every
        time to ensure they're up-to-date. Adding/removing nodes while
        serving will break the server, as it will not get notified and
        re-discover content."""
        import http.server

        self.__site = site
        self.__template_repository = template_repository

        self.__configuration = configuration
        self.__cache = cache
        output_path = pathlib.Path(
            self.__configuration['output_directory'])
        self.__publisher = TemplatePublisher(output_path, self.__site,
                                             self.__template_repository)

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = pathlib.PurePosixPath(self.path)

                if path.name == 'index.html':
                    path = path.parent

                if path not in self.server.cache:
                    node_path, cache = \
                        self.server.http_server._build_single_node(path)

                    if node_path is None:
                        return

                    if cache:
                        self.server.cache[path] = node_path
                else:
                    node_path = self.server.cache[path]

                self.send_response(200)

                content_type, _ = mimetypes.guess_type(path.name)
                if content_type:
                    self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(node_path.open('rb').read())

            def log_message(self, f, *args):
                self.server.log.info(f, *args)

        server_address = ('', self.__port)
        server = http.server.HTTPServer(server_address, RequestHandler)
        server.http_server = self
        server.log = self.__log
        server.cache = {}
        url = self.get_url()
        self.__log.info(f'Listening on {url}')

        if self.__open_browser:
            webbrowser.open(url)
        else:
            print(f'Listening on {url}')

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)
