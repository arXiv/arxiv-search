# Decision log

1. To get started quickly, we will start with an AWS Elasticsearch managed
   cluster running in the cloud. We may wish to run our own cluster in the
   future.
2. The search application itself well be deployed using mod_wsgi on
   classic servers.
3. The H1 application will run at /search rather than /find. When we deploy to
   production, links on the classic site will be updated to point to /search.
  * We will post a deprecation notice on the /find page.
  * We will continue to serve /find as a deprecated (and hidden!) interface for
    a little while.
  * We will monitor traffic at /find and /search to confirm that the vast
    majority of requests are to the new interface.
4. Because inferring the precise announcement date of past papers is not
   readily possible, we will use submission date for filtering and sort.
5. Because we anticipate that the search application is likely to change
   dramatically in the future from this "shim" version, we will implement
   advanced, simple, and author search as separate controllers with distinct
   query structures tailored toward replicating the existing (classic)
   functionality.
6. To support advanced search, we decided to index each version of a paper
   separately.
  * In simple and author search, old versions are simply excluded.
  * In advanced search, old versions will appear with a link to the most
    recent version.
  * When sorted by relevance in advanced search, current versions are boosted
    to prevent multiple versions of the same paper from clustering together.
