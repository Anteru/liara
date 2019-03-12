from .nodes import GeneratedNode
from .site import Site
from . import __version__
import datetime
import email


class FeedNode(GeneratedNode):
    def __init__(self, path):
        super().__init__(path)


class RSSFeedNode(FeedNode):
    def __init__(self, path, site: Site, metadata,
                 *, collection='', limit=10):
        super().__init__(path)
        self.__collection = collection
        self.__limit = limit
        self.__site = site
        self.__metadata = metadata

    def generate(self):
        from lxml.builder import E
        from lxml import etree
        import tzlocal

        items = reversed(list(self.__site.get_collection(
            self.__collection).nodes)[-self.__limit:])

        meta = self.__metadata
        tz = tzlocal.get_localzone()

        r = E.rss(version='2.0')

        c = E.channel(
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
    def __init__(self, path, site: Site, metadata,
                 *, collection='', limit=10):
        super().__init__(path)
        self.__collection = collection
        self.__limit = limit
        self.__site = site
        self.__metadata = metadata

    def generate(self):
        import json
        items = reversed(list(self.__site.get_collection(
            self.__collection).nodes)[-self.__limit:])

        meta = self.__metadata

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
