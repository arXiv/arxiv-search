"""
Provide hit highlighting to the search.

Highlighting requires amendation of the query as well as post-processing of
the returned results. :func:`.highlight` adds a highlighting part to the query
in the Elasticsearch DSL. :func:`.add_highlighting` performs post-processing
of the search results. :func:`.preview` generates a TeX-safe snippet for
abridged display in the search results.
"""

import re
from typing import Any

from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.response import Response
import bleach
from flask import escape

from .util import TEXISM

HIGHLIGHT_TAG_OPEN = '<span class="search-hit mathjax">'
HIGHLIGHT_TAG_CLOSE = '</span>'


def highlight(search: Search) -> Search:
    """
    Apply hit highlighting to the search, before execution.

    Parameters
    ----------
    search : :class:`.Search`

    Returns
    -------
    :class:`.Search`
        The search object that was originally passed, updated to include
        requests for hit highlighting.

    """
    # Highlight class .search-hit defined in search.sass
    search = search.highlight_options(
        pre_tags=[HIGHLIGHT_TAG_OPEN],
        post_tags=[HIGHLIGHT_TAG_CLOSE],
        require_field_match=False
    )
    search = search.highlight('title', type='plain', number_of_fragments=0)
    search = search.highlight('title.english', type='plain',
                              number_of_fragments=0)
    search = search.highlight('title.tex', type='plain',
                              number_of_fragments=0)

    search = search.highlight('comments', number_of_fragments=0)
    # Highlight any field the name of which begins with "author".
    search = search.highlight('author*')
    search = search.highlight('owner*')
    search = search.highlight('announced_date_first')
    search = search.highlight('submitter*')
    search = search.highlight('journal_ref', type='plain')
    search = search.highlight('acm_class', number_of_fragments=0)
    search = search.highlight('msc_class', number_of_fragments=0)
    search = search.highlight('doi', type='plain')
    search = search.highlight('report_num', type='plain')

    # Setting number_of_fragments to 0 tells ES to highlight the entire
    # abstract.
    search = search.highlight('abstract', number_of_fragments=0)
    search = search.highlight('abstract.tex', type='plain',
                              number_of_fragments=0)
    search = search.highlight('abstract.english', number_of_fragments=0)

    search = search.highlight('primary_classification*', type='plain',
                              number_of_fragments=0)
    return search


def preview(value: str, fragment_size: int = 400,
            start_tag: str = HIGHLIGHT_TAG_OPEN,
            end_tag: str = HIGHLIGHT_TAG_CLOSE) -> str:
    """
    Generate a snippet preview that doesn't breaking TeXisms or highlighting.

    Parameters
    ----------
    value : str
        The full text of the field, which we assume contains TeXisms and/or
        hit hightlighting tags.
    fragment_size : int
        The desired size of the preview (number of characters). The actual
        preview may be smaller or larger than this target, depending on where
        the TeXisms and highlight tags are located.
    start_tag : str
        The opening tag used for hit highlighting.
    end_tag: str
        The closing tag used for hit highlighting.

    Returns
    -------
    str
        A preview that is approximately ``fragment_size`` long.

    """
    # value = re.sub('')
    # value = value.replace('$$', '$')
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
    snippet = value[start:end].strip()
    last_open = snippet.rfind(HIGHLIGHT_TAG_OPEN)
    last_close = snippet.rfind(HIGHLIGHT_TAG_CLOSE)

    if last_open > last_close and last_open >= 0:
        snippet += HIGHLIGHT_TAG_CLOSE
    snippet = (
        ('&hellip;' if start > 0 else '')
        + snippet
        + ('&hellip;' if end < len(value) else '')
    )
    return snippet


# def _highlight(value: str, pattern: )


def add_highlighting(result: dict, raw: Response) -> dict:
    """
    Add hit highlighting to a search result.

    Parameters
    ----------
    result : dict
        Contains processed search result data destined for the caller.
    raw : :class:`.Response`
        A response from Elasticsearch.

    Returns
    -------
    dict
        The ``result`` object, updated with ``highlight`` and ``preview``
        items.

    """
    # There may or may not be highlighting in the result set.
    highlighted_fields = getattr(raw.meta, 'highlight', None)
    # ``meta.matched_queries`` contains a list of query ``_name``s that
    # matched. This is nice for non-string fields.
    matched_fields = getattr(raw.meta, 'matched_queries', [])

    # The values here will (almost) always be list-like. So we need to stitch
    # them together. Note that dir(None) won't return anything, so this block
    # is skipped if there are no highlights from ES.
    for field in dir(highlighted_fields):
        value = getattr(highlighted_fields, field)
        if hasattr(value, '__iter__'):
            value = '&hellip;'.join(value)

        if 'primary_classification' in field:
            field = 'primary_classification'

        # Non-TeX searches may hit inside of TeXisms. Highlighting those
        # fragments (i.e. inserting HTML) will break MathJax rendering.
        # To guard against this while preserving highlighting, we move
        # any highlighting tags from within TeXisms to encapsulate the
        # entire TeXism.
        if field in ['title', 'title.english',
                     'abstract', 'abstract.english']:
            value = _highlight_whole_texism(value)
            value = _escape(value)

        # A hit on authors may originate in several different fields, most
        # of which are not displayed. And in any case, author names may be
        # truncated. So instead of highlighting author names themselves, we
        # set a 'flag' that can get picked up in the template and highlight
        # the entire author field.
        if field.startswith('author') or field.startswith('owner') \
                or field.startswith('submitter'):
            result['match']['author'] = True
            continue

        result['highlight'][field] = value

    for field in matched_fields:
        if field not in result['highlight']:
            result['match'][field] = True

    # We just want to know whether there was a hit on the announcement date.
    result['match']['announced_date_first'] = (
        bool('announced_date_first' in matched_fields)
    )

    # If there is a hit in a TeX field, we prefer highlighting on that
    # field, since other tokenizers will clobber the TeX.
    for field in ['abstract', 'title']:
        if f'{field}.tex' in result['highlight']:
            result['highlight'][field] = \
                result['highlight'].pop(f'{field}.tex')

    for field in ['abstract.tex', 'abstract.english', 'abstract']:
        if field in result['highlight']:
            value = result['highlight'][field]
            abstract_snippet = preview(value)
            result['preview']['abstract'] = abstract_snippet
            result['highlight']['abstract'] = value
            break
    for field in ['title.english', 'title']:
        if field in result['highlight']:
            result['highlight']['title'] = result['highlight'][field]
            break
    return result


def _strip_highlight_and_enclose(match: Any) -> str:
    """Move any highlights within a TeXism to outside the TeXism."""
    value: str = match.group(0)
    if HIGHLIGHT_TAG_OPEN not in value and HIGHLIGHT_TAG_CLOSE not in value:
        return value
    value = value.replace(HIGHLIGHT_TAG_OPEN, "")
    value = value.replace(HIGHLIGHT_TAG_CLOSE, "")
    # If HTML was removed, we will assume that it was highlighting HTML.
    # if len(new_value) < len(value):
    value = f'{HIGHLIGHT_TAG_OPEN}{value}{HIGHLIGHT_TAG_CLOSE}'
    return value


def _highlight_whole_texism(value: str) -> str:
    """Move highlighting from within TeXism to encapsulate whole statement."""
    return re.sub(TEXISM, _strip_highlight_and_enclose, value)


def _escape(value: str) -> str:
    """
    Escape anything that isn't part of highlighting.

    Ideally, we'd use bleach.clean to do this for us. Unfortunately, it just
    gets too tripped up on equation content to use it reliably. Sometimes it
    throws exceptions when it hits equations that look like (but are not)
    HTML, and other times it panics. Since we really only have one tag-pair
    that we care to preserve, this approach works well enough for our purposes.
    """
    tag_o = HIGHLIGHT_TAG_OPEN
    tag_c = HIGHLIGHT_TAG_CLOSE
    _new = ""
    i = 0
    while True:
        i_o = value[i:].index(tag_o) if tag_o in value[i:] else None
        i_c = value[i:].index(tag_c) if tag_c in value[i:] else None
        if i_o is None and i_c is None:
            _new += str(escape(value[i:]))
            break
        if i_o is not None and i_c is not None:
            if i_o < i_c:
                _sub = str(escape(value[i:i + i_o])) + tag_o
                i += i_o + len(tag_o)
            elif i_c < i_o:
                _sub = str(escape(value[i:i + i_c])) + tag_c
                i += i_c + len(tag_c)
        elif i_o is not None and i_c is None:
            _sub = str(escape(value[i:i + i_o])) + tag_o
            i += i_o + len(tag_o)
        elif i_c is not None and i_o is None:
            _sub = str(escape(value[i:i + i_c])) + tag_c
            i += i_c + len(tag_c)
        _new += _sub
    return _new


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
                end_tag: str = HIGHLIGHT_TAG_CLOSE) -> int:
    """Find a fragment end that doesn't break TeXisms or HTML."""
    # Should match on either a TeXism or a TeXism enclosed in highlight tags.
    # TeXisms may be enclosed in pairs of $$ or $.
    ptn = r'|'.join([
        r'([\$]{2}[^\$]+[\$]{2})',
        r'([\$]{1}[^\$]+[\$]{1})',
        r'(%s[\$]{2}[^\$]+[\$]{2}%s)' % (start_tag, end_tag),
        r'(%s[\$]{1}[^\$]+[\$]{1}%s)' % (start_tag, end_tag),
        r'(%s[^\$]+%s)' % (start_tag, end_tag)
    ])
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
