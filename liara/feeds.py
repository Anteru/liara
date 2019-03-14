from .nodes import GeneratedNode, NodeKind
from .site import Site
from . import __version__
import datetime
import email


class FeedNode(GeneratedNode):
    def __init__(self, path):
        super().__init__(path)


class RSSFeedNode(FeedNode):
    """A `RSS 2.0 <http://www.rssboard.org/rss-specification>`_ based feed."""
    def __init__(self, path, site: Site,
                 *, collection='', limit=10):
        super().__init__(path)
        self.__collection = collection
        self.__limit = limit
        self.__site = site

    def generate(self):
        from lxml.builder import ElementMaker
        from lxml import etree
        import tzlocal

        items = reversed(list(self.__site.get_collection(
            self.__collection).nodes)[-self.__limit:])

        meta = self.__site.metadata
        tz = tzlocal.get_localzone()

        E = ElementMaker(nsmap={
            'atom': "http://www.w3.org/2005/Atom"
        })
        A = ElementMaker(namespace='http://www.w3.org/2005/Atom')
        r = E.rss(version='2.0')

        c = E.channel(
            # See: http://www.rssboard.org/rss-profile#namespace-elements-atom
            A.link(href=meta['base_url'] + str(self.path), rel='self',
                   type='application/rss+xml'),
            E.title(meta['title']),
            E.link(meta['base_url']),
            E.description(meta['description']),
            E.generator(f'Liara {__version__}'),
            E.language(meta['language']),
            E.copyright(meta['copyright']),
            E.lastBuildDate(email.utils.format_datetime(
                tz.localize(datetime.datetime.now()))),
        )

        for item in items:
            e = E.item(
                E.title(item.metadata['title']),
                E.link(meta['base_url'] + str(item.path)),
                E.pubDate(email.utils.format_datetime(item.metadata['date'])),
                E.guid(meta['base_url'] + str(item.path)),
                E.description(item.content)
            )
            c.append(e)
        r.append(c)

        self.content = etree.tostring(r)


class JsonFeedNode(FeedNode):
    """A `JSONFeed <https://jsonfeed.org/>`_ based feed."""
    def __init__(self, path, site: Site,
                 *, collection='', limit=10):
        super().__init__(path)
        self.__collection = collection
        self.__limit = limit
        self.__site = site

    def generate(self):
        import json
        items = reversed(list(self.__site.get_collection(
            self.__collection).nodes)[-self.__limit:])

        meta = self.__site.metadata

        result = {
            'version': 'https://jsonfeed.org/version/1',
            'title': meta['title'],
            'home_page_url': meta['base_url'],
            'feed_url': meta['base_url'] + str(self.path),
            'description': meta['description']
        }

        result_items = []
        for item in items:
            result_items.append({
                'id': meta['base_url'] + str(item.path),
                'title': item.metadata['title'],
                'date_published': item.metadata['date'].isoformat('T'),
                'url': meta['base_url'] + str(item.path),
                'content_html': item.content
            })

        result['items'] = result_items
        self.content = json.dumps(result)


class SitemapXmlFeedNode(FeedNode):
    """A `Sitemap 0.90 <https://www.sitemaps.org/>`_ based feed."""
    def __init__(self, path, site: Site):
        super().__init__(path)
        self.__site = site

    def generate(self):
        from lxml.builder import ElementMaker
        from lxml import etree

        E = ElementMaker(
            namespace='http://www.sitemaps.org/schemas/sitemap/0.9',
            nsmap={
                None: 'http://www.sitemaps.org/schemas/sitemap/0.9'
            })

        metadata = self.__site.metadata
        now = datetime.datetime.now()

        urlset = E.urlset()
        for node in self.__site.nodes:
            if node.kind not in {NodeKind.Document, NodeKind.Index}:
                continue

            url = E.url()
            url.append(E.loc(metadata['base_url'] + str(node.path)))

            if 'date' in node.metadata:
                url.append(E.lastmod(node.metadata['date'].isoformat()))
            else:
                url.append(E.lastmod(now.isoformat()))
            if node.kind == NodeKind.Index:
                # This is machine generated, so reduce priority
                url.append(E.priority('0'))
            urlset.append(url)
        self.content = etree.tostring(urlset)

