"""
Functions for processing search results (after execution).

The primary public function in this module is :func:`.to_documentset`.
"""

from math import floor
from typing import Union
from datetime import datetime

from elasticsearch_dsl.response import Response, Hit

from arxiv.base import logging
from search.domain import Document, Query, DocumentSet
from search.services.index.util import MAX_RESULTS
from search.services.index.highlighting import add_highlighting, preview

logger = logging.getLogger(__name__)
logger.propagate = False


def to_document(raw: Union[Hit, dict], highlight: bool = True) -> Document:
    """Transform an ES search result back into a :class:`.Document`."""
    # typing: ignore
    result: Document = {}

    result["match"] = {}  # Hit on field, but no highlighting.
    result["truncated"] = {}  # Preview is truncated.

    result.update(raw.to_dict()) # typing: ignore

    _add_announced_date_first(result, raw)

    _add_date(result, raw, "submitted_date")
    _add_date(result, raw, "submitted_date_first")
    _add_date(result, raw, "submitted_date_latest")    

    _add_amc_msc(result)

    try:
        result["score"] = raw.meta.score  # type: ignore
    except AttributeError:
        pass

    if "preview" not in result:
        result["preview"] = {}

    if "abstract" in result:
        result["preview"]["abstract"], result["truncated"]["abstract"] \
            = preview(result["abstract"])

    if highlight:
        result["highlight"] = {}
        result = add_highlighting(result, raw)

    return result


def to_documentset(
    query: Query, response: Response, highlight: bool = True
) -> DocumentSet:
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
    max_pages = int(MAX_RESULTS / query.size)
    n_pages_raw = response["hits"]["total"] / query.size
    n_pages = int(floor(n_pages_raw)) + int(int(n_pages_raw) % int(query.size) > 0)

    return {
        "metadata": {
            "start": query.page_start,
            "end": min(
                int(query.page_start + query.size), int(response["hits"]["total"])
            ),
            "total_results": response["hits"]["total"],
            "current_page": query.page,
            "total_pages": n_pages,
            "size": query.size,
            "max_pages": max_pages,
        },
        "results": [to_document(raw, highlight=highlight) for raw in response],
    }



def _add_announced_date_first(result:Document, raw:  Union[Hit, dict]) -> None:
    if "announced_date_first" in result:
        result["announced_date_first"] = datetime.strptime(
            raw["announced_date_first"], "%Y-%m"
        ).date()

def _add_date(result:Document, raw: Union[Hit, dict], key:str) -> None:
    """Update result with parsed date for key."""
    if key not in result:
        return    
    try:
        result[key] = datetime.strptime(raw[key], "%Y-%m-%dT%H:%M:%S%z")  # type: ignore
    except (ValueError, TypeError):
        logger.warning(f"Could not parse {key} as datetime")
        pass

def _add_amc_msc(result: Document) -> None:
    for key in ["acm_class", "msc_class"]:
        if key in result and result[key]:  # type: ignore
            result[key] = "; ".join(result[key])  # type: ignore
