from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class HeadingLevelFixupProcessor(Treeprocessor):
    """This processor demotes headings by one level.

    By default, Markdown starts headings with ``<h1>``, but in general the
    title will be provided by a template. This processor replaces each heading
    with the next-lower heading, and adds a ``demoted`` class.
    """
    def run(self, root):
        return self._demote_header(root)

    def _demote_header(self, element):
        if element.tag == 'h1':
            element.tag = 'h2'
            element.set('class', 'demoted')
        elif element.tag == 'h2':
            element.tag = 'h3'
            element.set('class', 'demoted')
        elif element.tag == 'h3':
            element.tag = 'h4'
            element.set('class', 'demoted')
        elif element.tag == 'h4':
            element.tag = 'h5'
            element.set('class', 'demoted')
        elif element.tag == 'h5':
            element.tag = 'h6'
            element.set('class', 'demoted')
        elif element.tag == 'h6':
            element.tag = 'h6'
            element.set('class', 'demoted')

        for e in element:
            self._demote_header(e)


class HeadingLevelFixupExtension(Extension):
    """Markdown extension for the :py:class:`HeadingLevelFixupProcessor`.
    """
    def extendMarkdown(self, md):
        md.treeprocessors.register(HeadingLevelFixupProcessor(md),
                                   'heading-level-fixup',
                                   100)
        md.registerExtension(self)
