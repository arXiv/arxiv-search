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


def _to_author(author_data: dict) -> Person:
    """Prevent e-mail, other extraneous data, from escaping."""
    data = {}
    for key, value in author_data.items():
        if key == 'email':
            continue
        elif key == 'name':
            key = 'full_name'
        if key not in Person.fields():
            continue
        data[key] = value
    return Person(**data)   # type: ignore


def to_document(raw: Union[Hit, dict], highlight: bool = True) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result: Dict[str, Any] = {}

    result['match'] = {}  # Hit on field, but no highlighting.
    result['truncated'] = {}    # Preview is truncated.

    logger.debug('Raw data is a %s instance', type(raw))
    for key in Document.fields():
        if type(raw) is Hit:
            if not hasattr(raw, key):
                continue
            value = getattr(raw, key)

        elif type(raw) is dict:
            if key not in raw:
                continue
            value = raw.get(key)
        else:
            continue

        # We want to prevent ES-specific data types from escaping the module
        # API.
        if isinstance(value, AttrList):
            value = value._l_
        elif isinstance(value, AttrDict):
            value = value.to_dict()

        if key == 'primary_classification':
            value = Classification(**value)  # type: ignore
        elif key == 'secondary_classification':
            value = [Classification(**v) for v in value]  # type: ignore
        elif key in ['authors', 'owners']:
            value = [_to_author(au) for au in value]
        elif key == 'submitter':
            value = _to_author(value)

        elif key == 'announced_date_first' and \
                value and isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m').date()
        elif key in ['submitted_date', 'submitted_date_first',
                     'submitted_date_latest']:
            try:
                value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
            except (ValueError, TypeError):
                logger.warning(f'Could not parse {key}: {value} as datetime')
                pass
        elif key in ['acm_class', 'msc_class'] and value:
            value = '; '.join(value)

        result[key] = value

    if type(raw) is Response:
        result['score'] = raw.meta.score    # type: ignore
    if type(result.get('abstract')) is str and highlight:
        if 'preview' not in result:
            result['preview'] = {}
        result['preview']['abstract'] = preview(result['abstract'])
        if result['preview']['abstract'].endswith('&hellip;'):
            result['truncated']['abstract'] = True

    if highlight and type(raw) is Response:
        result['highlight'] = {}
        logger.debug('%s: add highlighting to result',
                     raw.paper_id)  # type: ignore
        result = add_highlighting(result, raw)

    return Document(**result)   # type: ignore
    # See https://github.com/python/mypy/issues/3937


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

    return DocumentSet(**{  # type: ignore
        'metadata': {
            'start': query.page_start,
            'end': min(query.page_start + query.size,
                       response['hits']['total']),
            'total': response['hits']['total'],
            'current_page': query.page,
            'total_pages': N_pages,
            'size': query.size,
            'max_pages': max_pages
        },
        'results': [to_document(raw, highlight=highlight) for raw in response]
    })
    # See https://github.com/python/mypy/issues/3937
