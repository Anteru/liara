Writing & managing content
==========================

Every site requires some content to publish. In Liara, the main objects you'll be working with are the *site* which represents the whole content of your web site, and nodes. All content is stored in nodes: Every document, file, image, is a node in Liara's view of your site. Document nodes contain the textual content of your site. Liara also supports auto-generated :doc:`indices` which allow you to add navigation to your site -- for example, by creating an archive page. All nodes which can be targeted using templates (that is, document and index nodes) are commonly referred to as pages.

Once you've written the content, you'll need to set up templates and publishers to :doc:`publish <../publish/index>` your site.

.. toctree::
   :maxdepth: 2

   content

   collections
   generators
   indices
   metadata
   resources
   url-patterns
