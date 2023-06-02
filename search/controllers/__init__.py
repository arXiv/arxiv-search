"""
Houses controllers for search.

Each controller corresponds to a distinct search feature with its own request
handling logic. Each controller API exposes a ``search()`` function that
accepts a set of request parameters (``dict``-like) and returns a 3-tuple
of response data (``dict``), status code (``int``), and extra response headers
(``dict``).
"""
from http import HTTPStatus
from typing import Tuple, Dict, Any

from search.services import index
from search.domain import SimpleQuery


def health_check() -> Tuple[str, int, Dict[str, Any]]:
    """
    Exercise the connection with the search index with a real query.

    Returns
    -------
    dict
        Search result response data.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    """
    # We don't handle any exceptions here because we want the framework
    # exception handling to take care of it and log them.
    document_set = index.SearchSession.search(  # type: ignore
        SimpleQuery(search_field="all", value="theory")
    )
    if document_set["results"]:
        return "OK", HTTPStatus.OK, {}
    return "DOWN: document_set lacked results", HTTPStatus.INTERNAL_SERVER_ERROR, {}
