from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class HeadingLevelFixupProcessor(Treeprocessor):
    def run(self, root):
        return self.demote_header(root)

    def demote_header(self, element):
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
            self.demote_header(e)


class HeadingLevelFixupExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(HeadingLevelFixupProcessor(md),
                                   'heading-level-fixup',
                                   100)
        md.registerExtension(self)
