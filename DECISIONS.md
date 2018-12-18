# Decision log

## Initial design decisions - v0.1-0.4

1. To get started quickly, we will start with an AWS Elasticsearch managed
   cluster running in the cloud. We may wish to run our own cluster in the
   future.
2. The search application itself will be deployed using mod_wsgi on
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
6. We decided to index each individual version of a paper as a separate
   document, because we want to be able to support searches for individual
   versions in advanced search.
  * In simple and author search, we exclude results if they are not the most
    recent version of a paper.
  * In advanced search, we do not exclude any results. When sorted by relevance
    in advanced search, current versions are boosted to prevent multiple
    versions of the same paper from clustering together in the results.
7. We will truncate author names in search results for now, because papers with
   hundreds of authors take up enormous screen real-estate in the search
   results, and we are only seeking feature-parity with the classic system.
   When we address hit highlighting, we can show matching author names deep in
   author list to provide visual feedback to the user.

## Subsequent decisions

- 2018-12-18. Removing cross-list functionality in v0.1 was a regression. Users
  expect to be able to search by cross-list category just like primary
  category. We decided to include cross-list/secondary category in the
  all-fields search, and also add a cross-list option to the advanced search
  interface.
