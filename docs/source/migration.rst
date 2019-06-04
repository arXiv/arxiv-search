Migration Guide: Classic API to Search API
============================================

This guide presents instructions on how to migrate code that relied upon the classic API to the new conventions.


New Classic Endpoint
-----------------------
The starting point for the migration is changing the endpoint
from ``http://export.arxiv.org`` to ``https://arxiv.org/api/search/classic``.
This endpoint will be maintained as part of the arXiv-NG project.


New-style query strings
-------------------------
The former API used a syntax involving a single query string 
``search_query=``. The new API uses a fielded query string.


Content Negotiation (JSON, RSS)
---------------------------------
The classic API used RSS to represent search queries. The new API uses JSON to allow for easy interoop with web development practices.


JSON
''''''

http://127.0.0.1:5000/?query=ti:universes

::

    {
    "metadata": {
        "end": 6, 
        "query": [
        {
            "parameter": "title", 
            "value": "universes"
        }
        ], 
        "size": 50, 
        "start": 0, 
        "total": 6
    }, 
    "results": [
        {
        "canonical": "https://arxiv.org/abs/1801.01865v2", 
        "href": "http://127.0.0.1:5000/1801.01865v2", 
        "paper_id": "1801.01865", 
        "paper_id_v": "1801.01865v2", 
        "title": "Massless Particle Creation in Bianchi I Universes", 
        "version": 2
        }
    ]
    }




RSS
'''''

http://127.0.0.1:5000/query?search_query=ti:universes

::

    <?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns="http://www.w3.org/2005/Atom">
    <id>http://api.arxiv.org/</id>
    <title>arXiv Query: size: 50; terms: AND title=universes; include_fields: ['canonical', 'title', 'paper_id', 'href', 'version', 'paper_id_v', 'abstract', 'submitted_date', 'updated_date', 'comments', 'journal_ref', 'doi', 'primary_classification', 'secondary_classification', 'authors']</title>
    <updated>2019-06-04T06:01:31.365740+00:00</updated>
    <link href="https://api.arxiv.org/" type="application/atom+xml"/>
    <generator uri="http://lkiesow.github.io/python-feedgen" version="0.7.0">python-feedgen</generator>
    <opensearch:itemsPerPage>50</opensearch:itemsPerPage>
    <opensearch:totalResults>6</opensearch:totalResults>
    <opensearch:startIndex>0</opensearch:startIndex>
    <entry>
        <id>http://127.0.0.1:5000/astro-ph/0311033v4</id>
        <title>A new paradigm for the universe</title>
        <updated>2019-06-04T06:01:31.366602+00:00</updated>
        <link href="http://127.0.0.1:5000/astro-ph/0311033v4" rel="alternate" type="text/html"/>
        <summary>This book provides a completely new approach to understanding the universe. The main idea is that the principal objects in the universe form a spectrum unified by the presence of a massive or hypermassive black hole. These objects are variously called quasars, active galaxies and spiral galaxies. The key to understanding their dynamics is angular momentum and the key tool, and main innovative idea of this work, is a proper formulation of "Mach's principle" using Sciama's ideas. In essence, what is provided here is a totally new paradigm for the universe. In this paradigm, there is no big bang, and the universe is many orders of magnitude older than current estimates for its age. Indeed there is no natural limit for its age.</summary>
        <category term="astro-ph" scheme="http://arxiv.org://arxiv.org/schemas/atom"/>
        <published>2017-12-21T13:11:38-05:00</published>
        <arxiv:comment>198 pages, 81 figures (including jpg's). Version 4 has a good sketch for the source of the CMB (see appendix F)</arxiv:comment>
        <arxiv:primary_category term="astro-ph"/>
        <author>
        <name>Colin Rourke</name>
        </author>
    </entry>
    </feed>