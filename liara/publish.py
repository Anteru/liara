from .nodes import (
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


def _publish_with_template(output_path: pathlib.Path,
                           node: Union[DocumentNode, IndexNode],
                           site: Site,
                           site_template_proxy: SiteTemplateProxy,
                           template_repository) -> pathlib.Path:
    page = Page(node)
    file_path = pathlib.Path(str(output_path) + str(node.path))
    file_path.mkdir(parents=True, exist_ok=True)
    file_path = file_path / 'index.html'

    template = template_repository.find_template(node.path, site)
    file_path.write_text(template.render(
        site=site_template_proxy,
        page=page,
        node=node), encoding='utf-8')

    return file_path


class DefaultPublisher(Publisher):
    def __init__(self, output_path: pathlib.Path,
                 site: Site):
        self._output_path = output_path
        self._site = site

    def publish_resource(self, resource: ResourceNode):
        import os
        assert resource is not None
        file_path = pathlib.Path(str(self._output_path) + str(resource.path))
        os.makedirs(file_path.parent, exist_ok=True)
        file_path.write_bytes(resource.content)
        return file_path

    def publish_generated(self, generated: GeneratedNode):
        import os
        file_path = pathlib.Path(str(self._output_path) + str(generated.path))
        os.makedirs(file_path.parent, exist_ok=True)
        if isinstance(generated.content, bytes):
            file_path.write_bytes(generated.content)
        else:
            file_path.write_text(generated.content, encoding='utf-8')
        return file_path

    def publish_static(self, static: StaticNode):
        import shutil
        import os
        from contextlib import suppress
        assert static is not None
        file_path = pathlib.Path(str(self._output_path) + str(static.path))
        os.makedirs(file_path.parent, exist_ok=True)

        with suppress(FileExistsError):
            # Symlink requires an absolute path
            source_path = os.path.abspath(static.src)
            try:
                os.symlink(source_path, file_path)
            # If we can't symlink for some reason (for instance,
            # Windows does not support symlinks by default, we try to
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
