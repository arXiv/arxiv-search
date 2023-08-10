"""
Provide hit highlighting to the search.

Highlighting requires amendation of the query as well as post-processing of
the returned results. :func:`.highlight` adds a highlighting part to the query
in the Elasticsearch DSL. :func:`.add_highlighting` performs post-processing
of the search results. :func:`.preview` generates a TeX-safe snippet for
abridged display in the search results.
"""

import re
from typing import Any, Union, List, Tuple

from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response, Hit
from markupsafe import Markup, escape

import logging


from search.domain import Document
from search.services.index.util import TEXISM
from search.services.tex import math_positions, Math, isMath, \
    split_for_maths, position_f

logger = logging.getLogger(__name__)

HIGHLIGHT_TAG_OPEN = '<span class="search-hit mathjax">'
HIGHLIGHT_TAG_CLOSE = "</span>"


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
        pre_tags=[HIGHLIGHT_TAG_OPEN], post_tags=[HIGHLIGHT_TAG_CLOSE]
    )
    search = search.highlight("title", type="plain", number_of_fragments=0)
    search = search.highlight(
        "title.english", type="plain", number_of_fragments=0
    )
    search = search.highlight("title.tex", type="plain", number_of_fragments=0)

    search = search.highlight("comments", number_of_fragments=0)
    # Highlight any field the name of which begins with "author".
    search = search.highlight("author*")
    search = search.highlight("owner*")
    search = search.highlight("announced_date_first")
    search = search.highlight("submitter*")
    search = search.highlight("journal_ref", type="plain")
    search = search.highlight("acm_class", number_of_fragments=0)
    search = search.highlight("msc_class", number_of_fragments=0)
    search = search.highlight("doi", type="plain")
    search = search.highlight("report_num", type="plain")

    # Setting number_of_fragments to 0 tells ES to highlight the entire field.
    search = search.highlight("abstract", number_of_fragments=0)
    search = search.highlight(
        "abstract.tex", type="plain", number_of_fragments=0
    )
    search = search.highlight("abstract.english", number_of_fragments=0)
    return search


def preview(
    value: str,
    fragment_size: int = 400,
    start_tag: str = HIGHLIGHT_TAG_OPEN,
    end_tag: str = HIGHLIGHT_TAG_CLOSE,
) -> Tuple[str,bool]:
    """
    Generate an escaped preview snippet as Markup that doesn't break TeXisms or highlighting.

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
    bool
        If it was truncated.

    """
    if start_tag in value and end_tag in value:
        start = value.index(start_tag)
        end = value.index(end_tag) + len(end_tag)
        # Roll back the start until we hit a TeXism or HTML tag, or we get
        # roughly half the target fragment size.
        start_frag_size = round((fragment_size - (end - start)) / 2)
        c = value[start - 1]
        s = start
        while start - s < start_frag_size and s > 0:
            if c in "$>":  # This may or may not be an actual HTML tag or TeX.
                break  # But it doesn't hurt to play it safe.
            s -= 1
            c = value[s - 1]
        start = s
        # Move the start forward slightly, to find a word boundary.
        while c not in ".,!? \t\n$<" and start > 0:
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
    end += _end_safely(
        value[end:], remaining, start_tag=start_tag, end_tag=end_tag
    )

    start_trunc = start > 0
    end_trunc = end < len(value) 
    snippet = value[start:end].strip()
    last_open = snippet.rfind(start_tag)
    last_close = snippet.rfind(end_tag)

    if last_open > last_close and last_open >= 0:
        snippet += end_tag
    preview = ((Markup("&hellip;") if start_trunc else "")
               + escape(snippet)
               + (Markup("&hellip;") if end_trunc else ""))
    return preview, start_trunc or end_trunc


def add_highlighting(result: Document, raw: Union[Response, Hit]) -> Document:
    """
    Add hit highlighting to a search result.

    Parameters
    ----------
    result : dict
        Contains processed search result data destined for the caller.
    raw : :class:`.Response` or :class:`.Hit`
        A response object from Elasticsearch.

    Returns
    -------
    dict
        The ``result`` object, updated with ``highlight`` and ``preview``
        items.

    """
    # There may or may not be highlighting in the result set.
    highlighted_fields = getattr(raw.meta, "highlight", None)

    # ``meta.matched_queries`` contains a list of query ``_name``s that
    # matched. This is nice for non-string fields.
    matched_fields = getattr(raw.meta, "matched_queries", [])

    # The values here will (almost) always be list-like. So we need to stitch
    # them together. Note that dir(None) won't return anything, so this block
    # is skipped if there are no highlights from ES.
    for field in dir(highlighted_fields):
        if field.startswith("_"):
            continue
        value = getattr(highlighted_fields, field)
        if not hasattr(value, "__iter__"):
            value = [str(value)]  #str() due to things happening during mocked tests

        # Non-TeX searches may hit inside of TeXisms. Highlighting those
        # fragments (i.e. inserting HTML) will break MathJax rendering.
        # To guard against this while preserving highlighting, we move
        # any highlighting tags from within TeXisms to encapsulate the
        # entire TeXism.
        if field in ["title", "title.english", "abstract", "abstract.english"]:
            value = Markup("&hellip;").join([_highlight_whole_texism(item) for item in value])
        else:
            value = Markup("&hellip;".join(value))

        # A hit on authors may originate in several different fields, most
        # of which are not displayed. And in any case, author names may be
        # truncated. So instead of highlighting author names themselves, we
        # set a 'flag' that can get picked up in the template and highlight
        # the entire author field.
        if (
            field.startswith("author")
            or field.startswith("owner")
            or field.startswith("submitter")
        ):
            result["match"]["author"] = True
            continue

        result["highlight"][field] = value

    for field in matched_fields:
        if field not in result["highlight"]:
            result["match"][field] = True

    # These are from hits within child documents, e.g.
    # secondary_classification.
    inner_hits = getattr(raw.meta, "inner_hits", None)
    # We're using inner_hits to see which category in particular responded to
    # the query.
    if hasattr(inner_hits, "secondary_classification"):
        result["match"]["secondary_classification"] = [
            ih.category.id for ih in inner_hits.secondary_classification
        ]

    # We just want to know whether there was a hit on the announcement date.
    result["match"]["announced_date_first"] = bool(
        "announced_date_first" in matched_fields
    )

    # If there is a hit in a TeX field, we prefer highlighting on that
    # field, since other tokenizers will clobber the TeX.
    for field in ["abstract", "title"]:
        if f"{field}.tex" in result["highlight"]:
            result["highlight"][field] = result["highlight"][f"{field}.tex"]
            del result["highlight"][f"{field}.tex"]

    for field in ["abstract.tex", "abstract.english", "abstract"]:
        if field in result["highlight"]:
            value = result["highlight"][field]
            result["preview"]["abstract"], result["truncated"]["abstract"] \
                = preview(value)
            result["highlight"]["abstract"] = value
            break
    for field in ["title.english", "title"]:
        if field in result["highlight"]:
            result["highlight"]["title"] = result["highlight"][field]
            break

    return result


def _de_highlight_math(math: Union[str, Math]) -> List[Union[str,Math]]:
    """
    Moves highlight spans to outside of math.

    Tries to keep multiple opens and closes in math balanced.
    """
    has_open, has_close = HIGHLIGHT_TAG_OPEN in math, HIGHLIGHT_TAG_CLOSE in math
    if not has_open and not has_close:
        return [math]
    score = collapse_hl_tags_score(math)
    math = Math(math.replace(HIGHLIGHT_TAG_OPEN, "")
                .replace(HIGHLIGHT_TAG_CLOSE, ""))
    if score > 0:  # more opens than closes in math
        return [ HIGHLIGHT_TAG_OPEN * score , math]  # Balance the extra opens
    if score < 0: # more closes than opens in math
        return [ math, HIGHLIGHT_TAG_CLOSE * score ]
     # tags are balanced inside the math
    return [HIGHLIGHT_TAG_OPEN, math, HIGHLIGHT_TAG_CLOSE] # may need to rewrap with Math?

def _highlight_whole_texism(value: str) -> str:
    """
    Move highlighting from within TeXism to encapsulate whole statement.

    The overview is 
    1. The TeX positions are located
    2. The string is split into a list of strings on these boundaries
    3. Each TeX string has its tags moved out of it in a balanced way
    4. Each non-TeX string is split into span tags and non-span tags
    5. The list mapped so that non-TeX and TeX get escaped and span tags become Markup
    6. The list of strings joined.
    """
    pos = math_positions(value)
    if pos:
        splits = split_for_maths(pos, value)
    else:
        splits = [value] #no math found so use whole value

    corrected: List[Union[str,Math]] = []
    for txt in splits:
        if not isMath(txt):
            corrected.append(txt) # might want to escape non-tex here?
        else:
            corrected.extend(_de_highlight_math(txt)) # might want to escape tex here?

    return Markup(''.join( [_escape(part) for part in corrected ]))


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
    if isinstance(value, Math):
        return escape(value)
    if value in (tag_o, tag_c):
        return Markup(value)

    return _escape_nontex(value)

def _escape_nontex(value: str) -> str:
    """Escape non-tex that might have highlight spans."""
    _new = ''
    tag_pos =  _highlight_positions(value)
    if not tag_pos: 
        return escape(value)
    last = len(tag_pos)-1
    for ii in range(0, len(tag_pos)):
        start,end = tag_pos[ii]
        if ii == 0 and start !=0 : #anything before first tag            
            _new = escape(value[0:start])
            
        _new = _new + Markup(value[start:end])
        
        if ii != last:
            start_of_next_tag = tag_pos[ii+1][0]
            _new = _new + escape(value[end:start_of_next_tag])
        else:
            _new = _new + escape(value[end:])
        
    return Markup(_new)

def _start_safely(
    value: str,
    start: int,
    end: int,
    fragment_size: int,
    tolerance: int = 0,
    start_tag: str = HIGHLIGHT_TAG_OPEN,
    end_tag: str = HIGHLIGHT_TAG_CLOSE,
) -> int:
    # Try to maximize the length of the fragment up to the fragment_size, but
    # avoid starting in the middle of a tag or a TeXism.
    space_remaining = (fragment_size + tolerance) - (end - start)

    remainder = value[start - fragment_size : start]
    acceptable = value[start - fragment_size - tolerance : start]
    if end_tag in remainder:
        # Relative index of the first end tag.
        first_end_tag = value[start - space_remaining : start].index(end_tag)
        if start_tag in value[start - space_remaining : first_end_tag]:
            target_area = value[start - space_remaining : first_end_tag]
            first_start_tag = target_area.index(start_tag)
            return (start - space_remaining) + first_start_tag
    elif "$" in remainder:
        m = TEXISM.search(acceptable)
        if m is None:  # Can't get to opening
            return start - remainder[::-1].index("$") + 1
        return (start - fragment_size - tolerance) + m.start()

    # Ideally, we hit the fragment size without entering a tag or TeXism.
    return start - fragment_size


def _end_safely(
    value: str,
    remaining: int,
    start_tag: str = HIGHLIGHT_TAG_OPEN,
    end_tag: str = HIGHLIGHT_TAG_CLOSE,
) -> int:
    """Find a fragment end that doesn't break TeXisms or HTML."""
    # Should match on either a TeXism or a TeXism enclosed in highlight tags.
    # TeXisms may be enclosed in pairs of $$ or $.
    ptn = r"|".join(
        [
            r"([\$]{2}[^\$]+[\$]{2})",
            r"([\$]{1}[^\$]+[\$]{1})",
            r"(%s[\$]{2}[^\$]+[\$]{2}%s)" % (start_tag, end_tag),
            r"(%s[\$]{1}[^\$]+[\$]{1}%s)" % (start_tag, end_tag),
            r"(%s[^\$]+%s)" % (start_tag, end_tag),
        ]
    )
    m = re.search(ptn, value)
    if m is None:  # Nothing to worry about; the coast is clear.
        return remaining
    ptn_start = m.start()
    ptn_end = m.end()
    if remaining <= ptn_start:  # The ideal end falls before the next TeX/tag.
        return remaining
    elif ptn_end < remaining:  # The ideal end falls after the next TeX/tag.
        return ptn_end + _end_safely(
            value[ptn_end:], remaining - ptn_end, start_tag, end_tag
        )

    # We can't make it past the end of the next TeX/tag without exceeding the
    # target fragment size, so we will end at the beginning of the match.
    return ptn_start


_tagpattern = re.compile('(' + re.escape( HIGHLIGHT_TAG_OPEN) +
                         '|' + re.escape(HIGHLIGHT_TAG_CLOSE)+')')

def _highlight_positions(value:str) -> List[Tuple[int,int]]:
    """
    Gets list of highlight tag positions.
    
    This is the start and end of each tag, not start tag to end of end tag
    """
    matches = _tagpattern.finditer(value)
    return [match.span() for match in matches ]


def collapse_hl_tags_score( value: str ) -> int:
    """Returns a score that represents the balance of tags in value.

    0 means tags are balanced, -n means n extra closes, +N means N extra open tags.
    """
    pos = _highlight_positions(value)
    tags = [value[start:end] for start, end in pos]
    return sum([ 1 if tag == HIGHLIGHT_TAG_OPEN else -1 for tag in tags])
