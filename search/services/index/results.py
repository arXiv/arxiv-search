"""
Functions for processing search results (after execution).

The primary public function in this module is :func:`.to_documentset`.
"""

import re
from datetime import datetime
from math import floor
from typing import Any, Dict

from elasticsearch_dsl.response import Response
from search.domain import Document, Query, DocumentSet
from arxiv.base import logging

from .util import MAX_RESULTS, TEXISM
from .highlighting import add_highlighting, preview

logger = logging.getLogger(__name__)
logger.propagate = False


def _to_document(raw: Response) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result: Dict[str, Any] = {}
    result['highlight'] = {}
    result['match'] = {}  # Hit on field, but no highlighting.
    result['truncated'] = {}    # Preview is truncated.
    for key in Document.fields():
        if not hasattr(raw, key):
            continue
        value = getattr(raw, key)
        if key == 'announced_date_first' and value and isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m').date()
        if key in ['submitted_date', 'submitted_date_first',
                   'submitted_date_latest']:
            try:
                value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
            except (ValueError, TypeError):
                logger.warning(
                    f'Could not parse {key}: {value} as datetime'
                )
                pass
        if key in ['acm_class', 'msc_class'] and value:
            value = '; '.join(value)

        result[key] = value
    result['score'] = raw.meta.score
    if type(result['abstract']) is str:
        result['preview']['abstract'] = preview(result['abstract'])
        if result['preview']['abstract'].endswith('&hellip;'):
            result['truncated']['abstract'] = True

    logger.debug('%s: add highlighting to result', raw.paper_id)
    result = add_highlighting(result, raw)
    return Document(**result)   # type: ignore
    # See https://github.com/python/mypy/issues/3937


def to_documentset(query: Query, response: Response) -> DocumentSet:
    """
    Transform a response from ES to a :class:`.DocumentSet`.

    Parameters
    ----------
    query : :class:`.Query`
        The original search query.
    response : :class:`.Response`
        The response from Elasticsearch.

    Returns
    -------
    :class:`.DocumentSet`
        The set of :class:`.Document`s responding to the query on the current
        page, along with pagination metadata.

    """
    max_pages = int(MAX_RESULTS/query.page_size)
    N_pages_raw = response['hits']['total']/query.page_size
    N_pages = int(floor(N_pages_raw)) + \
        int(N_pages_raw % query.page_size > 0)
    logger.debug('got %i results', response['hits']['total'])

    return DocumentSet(**{  # type: ignore
        'metadata': {
            'start': query.page_start,
            'end': min(query.page_start + query.page_size,
                       response['hits']['total']),
            'total': response['hits']['total'],
            'current_page': query.page,
            'total_pages': N_pages,
            'page_size': query.page_size,
            'max_pages': max_pages
        },
        'results': [_to_document(raw) for raw in response]
    })
    # See https://github.com/python/mypy/issues/3937
