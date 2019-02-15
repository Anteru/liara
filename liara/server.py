from .nodes import (
    NodeKind
)
import pathlib
from .site import Site
from .template import TemplateRepository
from .publish import TemplatePublisher


class HttpServer:
    def __init__(self, site: Site, template_repository: TemplateRepository,
                 configuration):
        self.__site = site
        self.__template_repository = template_repository
        self.__configuration = configuration
        output_path = pathlib.Path(
            self.__configuration['output_directory'])
        self.__publisher = TemplatePublisher(output_path, self.__site,
                                             self.__template_repository)

    def _reload_template_paths(self):
        from .yaml import load_yaml
        template_configuration = pathlib.Path(self.__configuration['template'])
        configuration = load_yaml(template_configuration.open())
        self.__template_repository.update_paths(configuration['paths'])

    def _build_single_node(self, path: pathlib.PurePosixPath):
        """Build a single node.

        This is used for just-in-time page generation. Based on a request, a
        single node is built. Special rules apply to make sure this is
        useful for actual work -- for instance, document/resource nodes
        are always rebuilt from scratch, and for documents, we also reload
        all templates."""
        from collections import namedtuple
        result = namedtuple('BuildResult', ['path', 'cache'])
        node = self.__site.get_node(path)

        if node is None:
            print(f'Node not found for path: "{path}"')
            return

        # We always regenerate the content
        if node.kind in {NodeKind.Document, NodeKind.Resource}:
            node.reload()
            node.process()
            cache = False
        else:
            cache = True

        if node.kind == NodeKind.Document:
            self._reload_template_paths()

        return result(node.publish(self.__publisher), cache)

    def serve(self):
        """Serve the page.

        This does not build the whole page up-front, but rather serves each
        node individually just-in-time, making it very fast to start."""
        import http.server

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = pathlib.PurePosixPath(self.path)
                if path not in self.server.cache:
                    node_path, cache = \
                        self.server.http_server._build_single_node(path)

                    if cache:
                        self.server.cache[path] = node_path
                else:
                    node_path = self.server.cache[path]

                self.send_response(200)
                self.end_headers()
                self.wfile.write(node_path.open('rb').read())

        server_address = ('', 8080)
        server = http.server.HTTPServer(server_address, RequestHandler)
        server.http_server = self
        server.cache = {}
        print('Listening: http://127.0.0.1:8080')
        server.serve_forever()
