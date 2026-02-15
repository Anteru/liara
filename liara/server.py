# SPDX-FileCopyrightText: 2019 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from .nodes import (
    DataNode,
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
from urllib.parse import unquote
import traceback
import pygments
import pygments.lexers
import pygments.formatters


class _ServerState:
    __log = logging.getLogger('liara.HttpServer')

    def __init__(self, liara: Liara, site: Site, cache: Cache,
                 enable_admin: bool):
        self.__site = site
        self.__cache = cache
        self.__enable_admin = enable_admin

        output_path = pathlib.Path(
            liara._get_configuration()['output_directory'])
        self.__publisher = TemplatePublisher(output_path, self.__site,
                                             liara._get_template_repository())

    @property
    def enable_admin(self):
        return self.__enable_admin

    @property
    def site(self):
        return self.__site

    def _build_single_node(self, path: pathlib.PurePosixPath,
                           enable_admin: bool):
        """Build a single node.

        Build a single node on-demand. We assume the state is regenerated
        on any config changes, and the cache is cleared. As an optimization,
        we process resource and document nodes every time here, so we don't
        need to rediscover the whole content when a known content or
        resource node has changed.

        If ``enable_admin`` is set, this will also render data nodes."""
        from collections import namedtuple
        BuildResult = namedtuple('BuildResult', ['path', 'content', 'cache'])
        node = self.__site.get_node(path)

        if node is None:
            raise Exception(f'Could not find node for path: "{path}"')

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

        if isinstance(node, DataNode) and enable_admin:
            from .yaml import dump_yaml
            yaml_content = dump_yaml(node.content)

            html: str = pygments.highlight(
                yaml_content,
                pygments.lexers.get_lexer_by_name('yaml'),
                pygments.formatters.get_formatter_by_name(
                    'html',
                    full=True))

            return BuildResult(None, html.encode('utf-8'), False)

        assert isinstance(node, StaticNode) \
               or isinstance(node, DocumentNode) \
               or isinstance(node, GeneratedNode) \
               or isinstance(node, IndexNode) \
               or isinstance(node, ResourceNode)

        return BuildResult(node.publish(self.__publisher), None, cache)


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
    """Helper class to wrap calling ``serve_forever``."""
    def __init__(self, server: _HttpServer):
        super().__init__()
        self.__server = server

    def run(self):
        self.__server.serve_forever()

    def stop(self):
        self.__server.shutdown()


class _RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        assert isinstance(self.server, _HttpServer)
        with self.server.mutex:
            # Paths with spaces will get encoded as %20 for example,
            # we need to unquote here first
            path = pathlib.PurePosixPath(unquote(self.path))

            if path.name == '$admin' and self.server.state.enable_admin:
                self.__render_nodes()
                return

            if path.name == 'index.html':
                path = path.parent

            if path not in self.server.cache:
                try:
                    node_path, content, cache = \
                        self.server.state._build_single_node(
                            path,
                            self.server.state.enable_admin)
                except Exception:
                    self.send_response(500, 'Failed to render node')
                    self.wfile.write(traceback.format_exc().encode('utf-8'))
                    for line in traceback.format_stack():
                        self.wfile.write(line.encode('utf-8'))
                    return

                # Serve transient data immediately
                if content is not None:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(content)
                    return

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

    def log_message(self, format, *args):
        assert isinstance(self.server, _HttpServer)
        self.server.log.info(format, *args)

    def __render_nodes(self):
        from importlib.resources import files
        from jinja2 import Template
        from .util import _create_node_tree_for_site

        assert isinstance(self.server, _HttpServer)
        site = self.server.state.site

        for node in site.nodes:
            if node.kind == NodeKind.Static:
                assert (isinstance(node, StaticNode))
                node.update_metadata()

        def is_index_node(node):
            return node.kind == NodeKind.Index

        nodes = nodes = sorted(site.nodes, key=lambda x: x.path)
        root = _create_node_tree_for_site(nodes)
        t = Template(
            files('liara').joinpath('static', 'nodes.jinja2').read_text())
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(t.render(nodes=[root],
                                  is_index_node=is_index_node).encode('utf-8'))


class HttpServer:
    __log = logging.getLogger('liara.HttpServer')

    def get_url(self):
        """Get the URL at which the site is hosted."""
        return f'http://127.0.0.1:{self.__port}'

    def __init__(self, *, open_browser=True, port=8080, enable_admin=False):
        self.__open_browser = open_browser
        self.__port = port
        self.__server: _HttpServer | None = None
        self.__server_thread: threading.Thread | None = None
        self.__request_handler = _RequestHandler
        self.__enable_admin = enable_admin

    def stop(self):
        """Stop the server.

        This will stop the internal thread as well. It's safe to call this
        function multiple times."""
        if self.__server and self.__server_thread:
            self.__server.shutdown()
            self.__server_thread.join()

        self.__server = None
        self.__server_thread = None

    def reconfigure(self, liara: Liara, cache: Cache):
        """Replace the liara instance of this server on the fly.

        This can be only called after the server has been started using
        :py:meth:`start`."""
        server_state = _ServerState(liara, liara.discover_content(),
                                    cache, self.__enable_admin)

        assert self.__server
        self.__server.update_state(server_state)

    def start(self, liara: Liara, cache: Cache):
        """Serve the site with just-in-time processing.

        This does not build the whole site up-front, but rather builds nodes
        on demand. It will run the server in a separate thread, which needs
        to be shut down using :py:meth:`stop`.

        The server can be reconfigured to use a different liara instance
        using :py:meth:`reconfigure`, in which case it will keep running and
        switch seamlessly to the new instance.
        """
        server_state = _ServerState(liara, liara.discover_content(),
                                    cache, self.__enable_admin)

        server_address = ('', self.__port)
        self.__server = _HttpServer(server_address, self.__request_handler,
                                    server_state, self.__log)
        url = self.get_url()
        self.__log.info(f'Listening on {url}')

        if self.__open_browser:
            if self.__enable_admin:
                webbrowser.open(url + '/$admin')
            else:
                webbrowser.open(url)
        else:
            print(f'Listening on {url}')

        print('Use CTRL-C to stop the server')

        self.__server_thread = _ServerThread(self.__server)
        self.__server_thread.start()
