"""
Functions for processing search results (after execution).

The primary public function in this module is :func:`.to_documentset`.
"""

import re
from datetime import datetime
from math import floor
from typing import Any, Dict, Union

from elasticsearch_dsl.response import Response, Hit
from elasticsearch_dsl.utils import AttrList, AttrDict
from search.domain import Document, Query, DocumentSet, Classification, Person
from arxiv.base import logging

from .util import MAX_RESULTS, TEXISM
from .highlighting import add_highlighting, preview

logger = logging.getLogger(__name__)
logger.propagate = False


def to_document(raw: Union[Hit, dict], highlight: bool = True) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result: Document = {}

    result['match'] = {}  # Hit on field, but no highlighting.
    result['truncated'] = {}    # Preview is truncated.

    result.update(raw.__dict__['_d_'])

    # Parse dates to date/datetime objects.
    if 'announced_date_first' in result:
        result['announced_date_first'] = \
            datetime.strptime(raw['announced_date_first'], '%Y-%m').date()
    for key in ['', '_first', '_latest']:
        key = f'submitted_date{key}'
        if key not in result:
            continue
        try:
            result[key] = datetime.strptime(raw[key], '%Y-%m-%dT%H:%M:%S%z')
        except (ValueError, TypeError):
            logger.warning(f'Could not parse {key} as datetime')
            pass

    for key in ['acm_class', 'msc_class']:
        if key in result and result[key]:
            result[key] = '; '.join(result[key])

    try:
        result['score'] = raw.meta.score    # type: ignore
    except AttributeError:
        pass

    if highlight:   # type(result.get('abstract')) is str and
        result['highlight'] = {}
        logger.debug('%s: add highlighting to result', result['paper_id'])

        if 'preview' not in result:
            result['preview'] = {}

        if 'abstract' in result:
            result['preview']['abstract'] = preview(result['abstract'])
            if result['preview']['abstract'].endswith('&hellip;'):
                result['truncated']['abstract'] = True

        result = add_highlighting(result, raw)

    return result


def to_documentset(query: Query, response: Response, highlight: bool = True) \
        -> DocumentSet:
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
    max_pages = int(MAX_RESULTS/query.size)
    N_pages_raw = response['hits']['total']/query.size
    N_pages = int(floor(N_pages_raw)) + \
        int(N_pages_raw % query.size > 0)
    logger.debug('got %i results', response['hits']['total'])
    return {
        'metadata': {
            'start': query.page_start,
            'end': min(query.page_start + query.size,
                       response['hits']['total']),
            'total_results': response['hits']['total'],
            'current_page': query.page,
            'total_pages': N_pages,
            'size': query.size,
            'max_pages': max_pages
        },
        'results': [to_document(raw, highlight=highlight) for raw in response]
    }
