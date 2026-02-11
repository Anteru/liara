# SPDX-FileCopyrightText: 2019 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from .nodes import (
    Node,
    DocumentNode,
    IndexNode,
    Publisher,
    ResourceNode,
    StaticNode,
    GeneratedNode,
)
from .template import Page, SiteTemplateProxy, TemplateRepository
from .site import Site
import pathlib
from typing import (
    Union
)
import logging
from .util import local_now
from . import __version__ as liara_version
import datetime


class BuildContext:
    """Provides information about the current build."""
    version: str
    """The Liara version string (i.e. ``a.b.c``)"""

    timestamp: datetime.datetime
    """The current time when this node was processed"""

    def __init__(self, node: Union[DocumentNode, IndexNode]):
        self.timestamp = local_now()
        self.version = liara_version
        self.__node = node

    @property
    def last_modified_time(self):
        """Get the last modified time of the source file (if present)
        as a ``datetime`` instance. If there's no source file (for example,
        for indices), this returns the timestamp of the build itself."""

        if p := self.__node.src:
            # We want all timestamps to be in the same timezone
            return datetime.datetime.fromtimestamp(
                p.stat().st_mtime,
                tz=self.timestamp.tzinfo)

        return self.timestamp


def _publish_with_template(output_path: pathlib.Path,
                           node: Union[DocumentNode, IndexNode],
                           site: Site,
                           site_template_proxy: SiteTemplateProxy,
                           template_repository) -> pathlib.Path:
    log = logging.getLogger('liara.publish.TemplatePublisher')

    page = Page(node)
    file_path = pathlib.Path(str(output_path) + str(node.path))
    file_path.mkdir(parents=True, exist_ok=True)
    file_path = file_path / 'index.html'

    template = template_repository.find_template(node.path, site)
    log.debug('Publishing %s "%s" to "%s" using template "%s"',
              node.kind.name.lower(), node.path, file_path, template.path)
    file_path.write_text(template.render(
        site=site_template_proxy,
        page=page,
        node=node,
        build_context=BuildContext(node)
        ), encoding='utf-8')

    return file_path


class DefaultPublisher(Publisher):
    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    def __init__(self, output_path: pathlib.Path,
                 site: Site):
        self._output_path = output_path
        self._site = site

    def get_output_path(self, node: Node):
        return pathlib.Path(str(self._output_path) + str(node.path)).absolute()

    def publish_resource(self, resource: ResourceNode):
        import os
        assert resource is not None
        file_path = self.get_output_path(resource)
        os.makedirs(file_path.parent, exist_ok=True)
        if resource.content is None:
            self.__log.warning(
                'Resource node "%s" has no content, skipping', resource.path)
            return
        file_path.write_bytes(resource.content)
        return file_path

    def publish_generated(self, generated: GeneratedNode):
        import os
        if generated.content is None:
            self.__log.warning(
                'Generated node "%s" has no content, skipping', generated.path)
            return
        file_path = self.get_output_path(generated)
        os.makedirs(file_path.parent, exist_ok=True)
        if isinstance(generated.content, bytes):
            file_path.write_bytes(generated.content)
        else:
            assert isinstance(generated.content, str)
            file_path.write_text(generated.content, encoding='utf-8')
        return file_path

    def publish_static(self, static: StaticNode):
        import shutil
        import os
        from contextlib import suppress
        assert static is not None
        file_path = self.get_output_path(static)
        os.makedirs(file_path.parent, exist_ok=True)

        with suppress(FileExistsError, shutil.SameFileError):
            # Same file is triggered when trying to symlink again
            # Symlink requires an absolute path
            assert static.src
            source_path = os.path.abspath(static.src)
            try:
                os.symlink(source_path, file_path)
            # If we can't symlink for some reason (for instance,
            # Windows does not support symlinks by default), we try to
            # copy instead.
            except OSError:
                shutil.copyfile(source_path, file_path)

        return file_path


class TemplatePublisher(DefaultPublisher):
    def __init__(self, output_path: pathlib.Path, site: Site,
                 template_repository: TemplateRepository):
        super().__init__(output_path, site)
        self.__site_template_proxy = SiteTemplateProxy(self._site)
        self.__template_repository = template_repository

    def publish_document(self, document):
        assert document is not None
        return _publish_with_template(self._output_path, document,
                                      self._site,
                                      self.__site_template_proxy,
                                      self.__template_repository)

    def publish_index(self, index: IndexNode):
        assert index is not None
        return _publish_with_template(self._output_path, index,
                                      self._site,
                                      self.__site_template_proxy,
                                      self.__template_repository)
