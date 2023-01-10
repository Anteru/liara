Feeds
=====

Feeds provide a global overview over the site or a collection, typically in the form of a sitemap file or a RSS feed.

Definition
----------

A feed definition consists of:

- The type of the feed to be generated.
- The output path.
- An optional limit on the number of elements that will be included in the feed.
- An optional :doc:`collection <../content/collections>` to restrict the feed to.

Example
-------

.. code:: yaml

   rss:
     collection: blog
     path: /rss.xml
     limit: 10
   json:
     collection: blog
     path: /feed.json
     limit: 10
   sitemap:
     path: /sitemap.xml

This file will generate three feeds, one :py:class:`~liara.feeds.RSSFeedNode` which uses the last 10 posts of the ``blog`` collection, one :py:class:`~liara.feeds.JsonFeedNode` with the same configuration, and finally one :py:class:`~liara.feeds.SitemapXmlFeedNode` for the whole site.