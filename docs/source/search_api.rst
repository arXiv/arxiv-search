Search API (Alpha)
******************

Release `0.5.0-alpha` introduces support for a metadata search API service.
This release targets milestone H2: Search API, with the following specific
goals:

- H2.1: A search API is exposed via the API gateway, with feature-parity to
  classic "arXiv API".

  - Consider content negotiation to support legacy XML and JSON(-LD).

- H2.2: Opportunistic improvements, fixes, e.g. proper handling of UTF-8
  characters (ARXIVNG-257).
- H2.3: Deprecate classic arXiv API.


The current release supports only JSON serialization, provided by
:class:`search.routes.api.serialize.JSONSerializer`. An Atom/XML serializer
:class:`search.routes.api.serialize.AtomXMLSerializer` is planned but not yet
implemented.

A formal description of the API (OpenAPI 3.0) and resources (JSON Schema) can
be found at `<https://github.com/cul-it/arxiv-search/tree/develop/schema>`_.

The service endpoints are defined in :mod:`search.routes.api`:

- The root endpoint :func:`search.routes.api.search` supports queries using the
  same semantics as the advanced search UI.
- The paper metadata endpoint :func:`search.routes.api.paper` provides more
  detailed metadata for a specific arXiv e-print.

Requests are handled by the controllers in :mod:`search.controllers.api`, using
the :class:`search.domain.api.APIQuery` domain class.
