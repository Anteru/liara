from .nodes import (
    NodeKind
)
import pathlib
from .site import Site
from .template import TemplateRepository
from .publish import TemplatePublisher
from .cache import FilesystemCache
import logging
import webbrowser


class HttpServer:
    __log = logging.getLogger('liara.HttpServer')

    def __init__(self, site: Site, template_repository: TemplateRepository,
                 configuration, *, open_browser=True):
        self.__site = site
        self.__template_repository = template_repository
        self.__configuration = configuration
        self.__cache = FilesystemCache(pathlib.Path(
            self.__configuration['build.cache_directory']
        ))
        output_path = pathlib.Path(
            self.__configuration['output_directory'])
        self.__publisher = TemplatePublisher(output_path, self.__site,
                                             self.__template_repository)
        self.__open_browser = open_browser

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
        result = namedtuple('BuildResult', ['path', 'cache'])
        node = self.__site.get_node(path)

        if node is None:
            print(f'Could not find node for path: "{path}"')
            return (None, None,)

        # We always regenerate the content
        if node.kind in {NodeKind.Document, NodeKind.Resource}:
            node.reload()
            node.process(self.__cache)
            cache = False
        # We don't cache index nodes so templates get re-applied
        elif node.kind == NodeKind.Index:
            cache = False
        else:
            cache = True

        if node.kind == NodeKind.Document:
            self._reload_template_paths()

        return result(node.publish(self.__publisher), cache)

    def serve(self):
        """Serve the site with just-in-time processing.

        This does not build the whole site up-front, but rather builds nodes
        on demand. Nodes requiring templates are rebuilt from scratch every
        time to ensure they're up-to-date. Adding/removing nodes while
        serving will break the server, as it will not get notified and
        re-discover content."""
        import http.server

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = pathlib.PurePosixPath(self.path)
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
                self.end_headers()
                self.wfile.write(node_path.open('rb').read())

            def log_message(self, f, *args):
                self.server.log.info(f, *args)

        port = 8080
        server_address = ('', port)
        server = http.server.HTTPServer(server_address, RequestHandler)
        server.http_server = self
        server.log = self.__log
        server.cache = {}
        url = f'http://127.0.0.1:{port}'
        print(f'Listening on {url}')

        self.__site.set_metadata_item('base_url', url)

        if self.__open_browser:
            webbrowser.open(url)
        server.serve_forever()
