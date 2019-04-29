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
  all-fields search, add a cross-list field to the advanced search interface,
  and include cross-list classification in shortcut routes and the advanced
  interface's classification filter (with option to exclude).

- 2019-04-19. Werkzeug has its own versions of url parsing/quoting functions in
  ``urllib.parse`` (e.g. to handle MultiDicts). In previous versions we were
  using these to build/rebuild query URLs in search results, in
  `search.routes.ui.context_processors`. These functions are slow, however,
  running more than 3x more slowly than their built-in predecessors. If we
  are using ``urlencode`` on a ``MultiDict``, we can simply do
  ``urlencode(data.items(multi=True))``. Going forward, we will use only the
  built-in functions in ``urllib.parse`` unless there is a very strong reason
  to do otherwise.

- 2019-04-22. While convenient, dataclasses have significant performance
  overhead. Specifically, casting dataclasses from/to native Python structs
  runs around two orders of magnitude more costly than just initializing new
  dicts. This is fine if the number of instances is low. But in this case, we
  were using dataclasses to represent individual search results, and casting
  to/from dataclass representations without a whole lot of functional benefit.
  For this reason, we are using dataclasses only for "low-volume" structs like
  queries. For search results, we are now using
  [TypedDicts](https://www.python.org/dev/peps/pep-0589/). This gives us type
  checking machinery, is consistent with the [data domain](https://arxiv.github.io/arxiv-arxitecture/crosscutting/services.html#data-domain)
  concept in the arXiv service architecture, and is considerably more
  performant. In the future, we may want to consider moving entirely to
  TypedDict for consistency.
