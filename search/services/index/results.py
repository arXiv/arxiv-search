"""Functions for processing search results (after execution)."""

import re
import bleach
from datetime import datetime
from math import floor
from typing import Any

from elasticsearch_dsl.response import Response
from search.domain import Document, Query, DocumentSet
from arxiv.base import logging

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


def _start_safely(value: str, start: int, end: int, fragment_size: int,
                  tolerance: int = 0, start_tag: str = HIGHLIGHT_TAG_OPEN,
                  end_tag: str = HIGHLIGHT_TAG_CLOSE) -> int:
    # Try to maximize the length of the fragment up to the fragment_size, but
    # avoid starting in the middle of a tag or a TeXism.
    space_remaining = (fragment_size + tolerance) - (end - start)

    remainder = value[start - fragment_size:start]
    acceptable = value[start - fragment_size - tolerance:start]
    if end_tag in remainder:
        # Relative index of the first end tag.
        first_end_tag = value[start - space_remaining:start].index(end_tag)
        if start_tag in value[start - space_remaining:first_end_tag]:
            target_area = value[start - space_remaining:first_end_tag]
            first_start_tag = target_area.index(start_tag)
            return (start - space_remaining) + first_start_tag
    elif '$' in remainder:
        m = TEXISM.search(acceptable)
        if m is None:   # Can't get to opening
            return start - remainder[::-1].index('$') + 1
        return (start - fragment_size - tolerance) + m.start()

    # Ideally, we hit the fragment size without entering a tag or TeXism.
    return start - fragment_size


def _end_safely(value: str, remaining: int,
                start_tag: str = HIGHLIGHT_TAG_OPEN,
                end_tag: str = HIGHLIGHT_TAG_CLOSE):
    """Find a fragment end that doesn't break TeXisms or HTML."""
    # Should match on either a TeXism or a TeXism enclosed in highlight tags.
    ptn = r'(\$[^\$]+\$)|({}\$[^\$]+\${})'.format(start_tag, end_tag)
    m = re.search(ptn, value)
    if m is None:   # Nothing to worry about; the coast is clear.
        return remaining

    ptn_start = m.start()
    ptn_end = m.end()
    if remaining <= ptn_start:  # The ideal end falls before the next TeX/tag.
        return remaining
    elif ptn_end < remaining:   # The ideal end falls after the next TeX/tag.
        return ptn_end + _end_safely(value[ptn_end:], remaining - ptn_end,
                                     start_tag, end_tag)

    # We can't make it past the end of the next TeX/tag without exceeding the
    # target fragment size, so we will end at the beginning of the match.
    return ptn_start


def _preview(value: str, fragment_size: int = 400,
             start_tag: str = HIGHLIGHT_TAG_OPEN,
             end_tag: str = HIGHLIGHT_TAG_CLOSE) -> str:
    """Generate a snippet preview for highlighted text."""
    if start_tag in value and end_tag in value:
        start = value.index(start_tag)
        end = value.index(end_tag) + len(end_tag)
        # Roll back the start until we hit a TeXism or HTML tag, or we get
        # roughly half the target fragment size.
        start_frag_size = round((fragment_size - (end - start)) / 2)
        c = value[start - 1]
        s = start
        while start - s < start_frag_size and s > 0:
            if c in '$>':   # This may or may not be an actual HTML tag or TeX.
                break       # But it doesn't hurt to play it safe.
            s -= 1
            c = value[s - 1]
        start = s
        # Move the start forward slightly, to find a word boundary.
        while c not in '.,!? \t\n$<' and start > 0:
            start += 1
            c = value[start - 1]
    else:
        # There is no highlighting; we'll start at the beginning, and find
        # a safe place to end.
        start = 0
        end = 1

    # Jump the end forward until we consume (as much as possible of) the
    # rest of the target fragment size.
    remaining = max(0, fragment_size - (end - start))
    end += _end_safely(value[end:], remaining, start_tag=start_tag,
                       end_tag=end_tag)
    return (
        ('&hellip;' if start > 0 else '')
        + value[start:end].strip()
        + ('&hellip;' if end < len(value) else '')
    )


def _add_highlighting(result: dict, raw: Response) -> dict:
    """Add hit highlighting to a search result."""
    if not hasattr(raw.meta, 'highlight'):
        return result   # Nothing to do.

    result['highlight'] = {}
    # The values here will (almost) always be list-like. So we need to stitch
    # them together.
    for field in dir(raw.meta.highlight):
        value = getattr(raw.meta.highlight, field)
        if hasattr(value, '__iter__'):
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

    for field in ['abstract.tex', 'abstract_utf8', 'abstract']:
        if field in result['highlight']:
            value = result['highlight'][field]
            abstract_snippet = _preview(value)
            result['preview']['abstract'] = abstract_snippet
            result['highlight']['abstract'] = value
            break
    return result


def _to_document(raw: Response) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result = {'preview': {}}
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
    if type(result['abstract']) is str:
        result['preview']['abstract'] = _preview(result['abstract'])
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
