from .nodes import DocumentNode
from .site import Site
import pathlib


def validate_document_links(document: DocumentNode, site: Site):
    """Validate all ``<a href="">`` and ``<img src="">`` links in a document."""
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
        # The redirection table contains full paths including the trailing
        # index.html, so if we find a link `/foo/bar/`, we also check
        # `/foo/bar/index.html` in case a redirection is present.
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
