arXiv Search
************

Context
=======

The arXiv search system provides a faceted search experience to arXiv readers,
as a part of the core arXiv website. Readers can search by specific metadata
fields, and by full-text content. The search system also supports future
development to improve relevance, paper suggestions (e.g. based on the paper
that the reader is currently viewing), and suggestions based on reading
history.

The search system also provides programmatic access to arXiv metadata via
the API Gateway. API consumers can perform complex searches via RESTful APIs.
Resources provided by the API are linked to resources provided by other APIs
in the arXiv system, to facilitate discovery.

Finally, the search system acts as a secondary data store for some other arXiv
subsystems within the :ref:`enhancement & discovery area of concern
<enhancement-and-discovery>`. For example, the RSS feed API.

The search system subscribes to notifications about new publications and
full text content brokered by AWS Kinesis. When the full text content is
available, the search system retrieves the relevant metadata and content from
the :ref:`publication-metadata-store` and plain text store, respectively, and
updates the search index.

Subsystems
==========

The core of the search system is an ElasticSearch index, provided by the `AWS
Elasticsearch Service <https://aws.amazon.com/elasticsearch-service/>`.

The search application, implemented in Flask and deployed on EC2, provides
both the user-facing interface and REST API. The search application is only
responsible for reading from ES. The REST API routes are proxied by the API
Gateway; those routes use client certificate validation to limit requests to
the gateway only. See also :ref:`web-application-architecture`.

An agent application is responsible for coordinating updates to the ES index.
The agent subscribes to notifications about the availability of plain text for
new publications delivered by the Kinesis broker. The agent makes requests
to the metadata repository and the plain text store, transforms those data
into a search document, and sends that document to ES. The agent is deployed
in a private subnet, on a small dedicated EC2 instance.
