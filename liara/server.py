from .nodes import (
    DocumentNode,
    GeneratedNode,
    IndexNode,
    NodeKind,
    ResourceNode,
    StaticNode,

    _process_node_sync
)
import pathlib
from . import Liara
from .publish import TemplatePublisher
from .cache import Cache
from .site import Site
import logging
import webbrowser
import mimetypes
import http.server
import threading

class _ServerState:
    __log = logging.getLogger('liara.HttpServer')

    def __init__(self, liara: Liara, site: Site, cache: Cache):
        self.__site = site
        self.__cache = cache
        
        output_path = pathlib.Path(
            liara._get_configuration()['output_directory'])
        self.__publisher = TemplatePublisher(output_path, self.__site,
                                             liara._get_template_repository())

    def _build_single_node(self, path: pathlib.PurePosixPath):
        """Build a single node.

        Build a single node on-demand. We assume the state is regenerated
        on any config changes, and the cache is cleared. As an optimization,
        we process resource and document nodes every time here, so we don't
        need to rediscover the whole content when a known content or
        resource node has changed."""
        from collections import namedtuple
        BuildResult = namedtuple('BuildResult', ['path', 'cache'])
        node = self.__site.get_node(path)

        if node is None:
            self.__log.warning(f'Could not find node for path: "{path}"')
            return (None, None,)

        # We always regenerate the content
        match node.kind:
            case NodeKind.Document | NodeKind.Resource:
                assert isinstance(node, DocumentNode) \
                    or isinstance(node, ResourceNode)
                node.reload()
                args = {
                    '$data': self.__site.merged_data
                }
                _process_node_sync(node, self.__cache, **args)
                cache = False
            case NodeKind.Generated:
                assert isinstance(node, GeneratedNode)
                node.generate()
                cache = False
            # We don't cache index nodes so templates get re-applied
            case NodeKind.Index:
                cache = False
            case _:
                cache = True

        assert isinstance(node, StaticNode) \
               or isinstance(node, DocumentNode) \
               or isinstance(node, GeneratedNode) \
               or isinstance(node, IndexNode) \
               or isinstance(node, ResourceNode)

        return BuildResult(node.publish(self.__publisher), cache)


class _HttpServer(http.server.HTTPServer):
    def __init__(self, address, request_handler_class,
                 state: _ServerState,
                 log: logging.Logger):
        self.state = state
        self.log = log
        self.mutex = threading.Lock()
        self.cache: dict[pathlib.PurePosixPath, pathlib.Path] = {}
        super().__init__(address, request_handler_class)

    def update_state(self, new_state: _ServerState):
        with self.mutex:
            self.state = new_state


class _ServerThread(threading.Thread):
    def __init__(self, server: _HttpServer):
        super().__init__()
        self.__server = server

    def run(self):
        self.__server.serve_forever()

    def stop(self):
        self.__server.shutdown()


class HttpServer:
    __log = logging.getLogger('liara.HttpServer')

    def get_url(self):
        return f'http://127.0.0.1:{self.__port}'

    def __init__(self, *, open_browser=True, port=8080):
        self.__open_browser = open_browser
        self.__port = port
        self.__server: _HttpServer | None = None
        self.__server_thread: threading.Thread | None = None

    def stop(self):

        if self.__server and self.__server_thread:
            self.__server.shutdown()
            self.__server_thread.join()

        self.__server = None
        self.__server_thread = None

    def reconfigure(self, liara: Liara, cache: Cache):
        server_state = _ServerState(liara, liara.discover_content(),
                            cache)
        
        assert self.__server
        self.__server.update_state(server_state)

    def start(self, liara: Liara, cache: Cache):
        """Serve the site with just-in-time processing.

        This does not build the whole site up-front, but rather builds nodes
        on demand. Nodes requiring templates are rebuilt from scratch every
        time to ensure they're up-to-date. Adding/removing nodes while
        serving will break the server, as it will not get notified and
        re-discover content."""
        import http.server
        server_state = _ServerState(liara, liara.discover_content(),
                                    cache)

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                assert isinstance(self.server, _HttpServer)
                with self.server.mutex:
                    path = pathlib.PurePosixPath(self.path)

                    if path.name == 'index.html':
                        path = path.parent

                    if path not in self.server.cache:
                        node_path, cache = \
                            self.server.state._build_single_node(path)

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
                assert isinstance(self.server, _HttpServer)
                self.server.log.info(f, *args)

        server_address = ('', self.__port)
        self.__server = _HttpServer(server_address, RequestHandler,
                                    server_state, self.__log)
        url = self.get_url()
        self.__log.info(f'Listening on {url}')
        # Only reopen if we didn't open it previously
        if self.__open_browser and not self.__server:
            webbrowser.open(url)
        else:
            print(f'Listening on {url}')

        print('Use CTRL-C to stop the server')

        self.__server_thread = _ServerThread(self.__server)
        self.__server_thread.start()
