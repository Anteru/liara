Publishing
==========

During publishing, your pages (i.e. document and index nodes) are converted to Html pages by applying :doc:`templates` to them. Additionally, Liara can also generate outputs like RSS feeds, site maps, and static routes for your web server at this stage.

Once the output is generated, you can upload it to any web server capable of hosting static Html like Apache, NGINX, Caddy, or others. Typically you'll want to use a tool like ``rsync`` for this.

.. toctree::
   :maxdepth: 2

   feeds
   processing
   static-routes
   templates
