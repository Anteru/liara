from .nodes import DocumentNode
from .site import Site
import pathlib


def validate_document_links(document: DocumentNode, site: Site):
    """Validate all ``<a href="">`` and ``<img src="">`` links in a document.

    This runs before templates are applied, but after content has been
    processed."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(document.content, 'lxml')

    def validate_link(link):
        if link is None:
            return

        if link.startswith('//') \
                or link.startswith('http://') \
                or link.startswith('https://') \
                or link.startswith('#'):
            return

        link = pathlib.PurePosixPath(link)

        # Special case handling for index.html:
        # We try the path with index.html, as redirections need to use the full
        # path. I.e. if there's a redirection from /foo/bar/index.html, and
        # a link references /foo/bar, then we will find the redirection this
        # way.
        index_url = link / 'index.html'
        if index_url in site.urls:
            return

        if link not in site.urls:
            print(f'"{link}" referenced in "{document.path}" does not exist')

    for link in soup.find_all('a'):
        target = link.attrs.get('href', None)
        validate_link(target)

    for image in soup.find_all('img'):
        target = image.attrs.get('src', None)
        validate_link(target)
