Search Interface
****************

The current version of the arXiv search application is designed to meet the
goals outlined in arXiv-NG milestone H1: Replace Legacy Search.

- H1.1. Replace the current advanced search interface, search results, and
  search by author name.
- H1.2. The search result view should support pagination, and ordering by
  publication date or relevance.
- H1.3. An indexing agent updates the search index at publication time in
  response to a Kinesis notification, using metadata from the docmeta endpoint
  in the classic system.

Key Requirements
================

- Simple search:

  - Users should be able to search for arXiv papers by title, author, and
    abstract.
  - Searches can originate from any part of the arXiv.org site, via the
    search bar in the site header.

- Advanced search:

  - Users can search for papers using boolean combinations of search terms on
    title, author names, and/or abstract.
  - Users can filter results by primary classification, and submission date.
  - Submission date supports prior year, specific year, and date range.

- Author name search:

  - Users should be able to search for papers by author name.
  - This should support queries originating on the abs page, and in search
    results.

- UI: The overall flavor of the search views should be substantially
  similar to the classic views, but with styling that improves
  readability, usability, and accessibility.

Quality Goals
=============
- Code quality:

  - 90% test coverage on Python components that we develop/control.
  - Linting: ``pylint`` passes with >= 9/10.
  - Documentation: ``pydocstyle`` passes.
  - Static checking: ``mypy`` passes.

- Performance & reliability:

  - Response time: 99% of requests have a latency of 1 second or less.
  - Error rate: parity with classic search.
  - Request rate: support request volume of existing search * safety factor 3.

- Accessibility: meet or exceed WCAG 2.0 level A for accessibility.

Constraints
===========
- Must be implemented in Python/Flask, and be deployable behind Apache as a
  Python/WSGI application.
- The search application itself must be stateless. It must be able to connect
  to an arbitrary ElasticSearch cluster, which can be specified via
  configuration.
- Notifications about new content are delivered via the Kinesis notification
  broker.
