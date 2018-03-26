"""Functions for processing search results (after execution)."""

import re
import bleach
from datetime import datetime
from math import floor
from typing import Any

from elasticsearch_dsl.response import Response
from search.domain import Document, Query, DocumentSet
from search import logging

from .util import MAX_RESULTS, HIGHLIGHT_TAG_OPEN, HIGHLIGHT_TAG_CLOSE

TEXISM = re.compile(r'(\$[^\$]+\$)')

logger = logging.getLogger(__name__)


def _strip_highlight_and_enclose(match: Any) -> str:
    # typing: ignore
    value: str = match.group(0)
    new_value = bleach.clean(value, strip=True, tags=[])

    # If HTML was removed, we will assume that it was highlighting HTML.
    if len(new_value) < len(value):
        return f'{HIGHLIGHT_TAG_OPEN}{new_value}{HIGHLIGHT_TAG_CLOSE}'
    return value


def _highlight_whole_texism(value: str) -> str:
    """Move highlighting from within TeXism to encapsulate whole statement."""
    return re.sub(TEXISM, _strip_highlight_and_enclose, value)


def _add_highlighting(result: dict, raw: Response) -> dict:
    """Add hit highlighting to a search result."""
    if hasattr(raw.meta, 'highlight'):
        result['highlight'] = {}
        # Since there may be more than one hit per field, the values here will
        # (almost) always be list-like. So we need to stitch them together.
        for field in dir(raw.meta.highlight):
            value = getattr(raw.meta.highlight, field)
            if hasattr(value, '__iter__'):
                # We want to keep the abstract fragment short, so we'll only
                # take the first two hits.
                if 'abstract' in field:
                    value = (
                        '&hellip;'
                        + ('&hellip;'.join(value[:2]))
                        + '&hellip;'
                    )
                else:
                    value = '&hellip;'.join(value)

            # Non-TeX searches may hit inside of TeXisms. Highlighting those
            # fragments (i.e. inserting HTML) will break MathJax rendering.
            # To guard against this while preserving highlighting, we move
            # any highlighting tags from within TeXisms to encapsulate the
            # entire TeXism.
            if field in ['title', 'title_utf8', 'abstract']:
                value = _highlight_whole_texism(value)
            result['highlight'][field] = value

        # If there is a hit in a TeX field, we prefer highlighting on that
        # field, since other tokenizers will clobber the TeX.
        for field in ['abstract', 'abstract_utf8', 'title', 'title_utf8']:
            if f'{field}.tex' in result['highlight']:
                result['highlight'][field] = \
                    result['highlight'].pop(f'{field}.tex')
    return result


def _to_document(raw: Response) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result = {}
    for key in Document.fields():
        if not hasattr(raw, key):
            continue
        value = getattr(raw, key)
        if key in ['submitted_date', 'submitted_date_first',
                   'submitted_date_latest']:
            try:
                value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
            except (ValueError, TypeError):
                logger.warning(
                    f'Could not parse {key}: {value} as datetime'
                )
                pass

        result[key] = value
    result['score'] = raw.meta.score

    result = _add_highlighting(result, raw)

    return Document(**result)   # type: ignore
    # See https://github.com/python/mypy/issues/3937


def to_documentset(query: Query, response: Response) -> DocumentSet:
    """Transform a response from ES to a :class:`.DocumentSet`."""
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
