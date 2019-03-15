from .nodes import DocumentNode
from .site import Site
import pathlib
from typing import Dict, List
from enum import Enum, auto
from collections import defaultdict


def _extract_links(document: DocumentNode):
    """Extract all links from ``<a>`` and ``<img>`` tags in a document.

    This assumes the document has been already processed into valid Html.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(document.content, 'lxml')

    for item in soup.find_all(['img', 'a']):
        if item.name == 'img':
            target = item.attrs.get('src', None)
        elif item.name == 'a':
            target = item.attrs.get('href', None)

        if target and not target.startswith('#'):
            yield target


class LinkType(Enum):
    Internal = auto()
    External = auto()


def _is_internal_link(link: str) -> bool:
    """Check if a link is internal.

    A link is considered internal if it starts with a single slash (not two,
    as this indicates a link using the same protocol.)
    """
    if len(link) >= 2:
        return link[0] == '/' and link[1] != '/'
    else:
        return link[0] == '/'


def gather_links(documents, link_type: LinkType) \
        -> Dict[str, List[pathlib.PurePosixPath]]:
    """Gather links across documents.

    :return: A dictionary containing a link, and the list of document paths
             in which this link was found.
    """
    result = defaultdict(list)

    for document in documents:
        links = _extract_links(document)
        for link in links:
            if link_type == LinkType.Internal and not _is_internal_link(link):
                continue
            elif link_type == LinkType.External and _is_internal_link(link):
                continue

            result[link].append(document.path)

    return result


def validate_internal_links(links: Dict[str, List[pathlib.PurePosixPath]],
                            site: Site):
    """Validate internal links.

    For each link, check if it exists inside the provided site. If not, an
    error is printed indicating the link and the documents referencing it."""

    for link, sources in links.items():
        link = pathlib.PurePosixPath(link)

        # Special case handling for index.html:
        # The redirection table contains full paths including the trailing
        # index.html, so if we find a link `/foo/bar/`, we also check
        # `/foo/bar/index.html` in case a redirection is present.
        index_url = link / 'index.html'
        if index_url in site.urls:
            continue

        if link not in site.urls:
            for source in sources:
                print(f'"{link}" referenced in "{source}" does not exist')


def _check_external_link(url):
    """Issue a request to the external URL and check for a valid response.
    """
    import requests
    ok = False
    try:
        r = requests.get(url, timeout=1)
        if r.status_code == 200:
            ok = True
        else:
            error = f'got {r.status_code}, expected 200'
    except requests.exceptions.ConnectionError:
        error = "connection error"
    except requests.exceptions.ConnectTimeout:
        error = "connection timeout"
    except requests.exceptions.ReadTimeout:
        error = "read timeout"
    except requests.exceptions.TooManyRedirects:
        error = "too many redirects"
    except Exception as e:
        error = str(e)

    if not ok:
        return (False, url, error,)
    else:
        return (True, url, None,)


def validate_external_links(links: Dict[str, List[pathlib.PurePosixPath]]):
    """Validate external links.

    This issues a request for each link, and checks if it connects correctly.
    If not, an error is printed indicating the link and the documents
    referencing it."""
    import multiprocessing

    with multiprocessing.Pool() as pool:
        result = pool.imap_unordered(_check_external_link, links.keys())

        for r in result:
            if not r[0]:
                for source in links[r[1]]:
                    print(f'Link "{r[1]}", referenced in "{source}" failed '
                          f'with: {r[2]}')
