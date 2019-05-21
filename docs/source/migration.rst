Migration Guide: Classic API to Search API
============================================

This guide presents instructions on how to migrate code that relied upon the classic API to the new conventions.

New Classic Endpoint
-----------------------
The starting point for the migration is changing the endpoint
from ``http://export.arxiv.org`` to ``https://arxiv.org/api/search/classic``. This will be maintained through XXXX.

New-style query strings
-------------------------
The former API used a syntax involving a single query string ``search_query=``. The new API uses a fielded query string.

Content Negotiation (JSON, RSS)
---------------------------------
The classic API used RSS to represent search queries. The new API
