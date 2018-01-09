"""Search controllers."""

from typing import Tuple, Dict, Any
from search.services import index, fulltext, metadata
from search.process import query
from search import status

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


def health() -> Response:
    """Check integrations."""
    return {'index': index.ok()}, status.HTTP_200_OK, {}


def search(request_params: dict) -> Response:
    """
    Perform a search with the provided parameters.

    Parameters
    ----------
    request_params : dict

    Returns
    -------
    dict
        Search result response data.
    int
        HTTP status code.
    dict
        Headers to add to the response.
    """
    response_data = {}
    if 'query' in request_params:
        response_data['query'] = request_params.pop('query')
        try:
            response_data['results'] = index.search(query.prepare(request_params))
        except ValueError as e:    #
            response_data['results'] = None   # TODO: handle this
        except IOError as e:
            response_data['results'] = None   # TODO: handle this
    return response_data, status.HTTP_200_OK, {}


def retrieve_document(document_id: str) -> Response:
    """
    Retrieve an arXiv paper by ID.

    Parameters
    ----------
    document_id : str
        arXiv identifier for the paper.

    Returns
    -------
    dict
        Metadata about the paper.
    int
        HTTP status code.
    dict
        Headers to add to the response.
    """
    try:
        result = index.get_document(document_id)
    except ValueError as e:    #
        result = None   # TODO: handle this
    except IOError as e:
        result = None   # TODO: handle this
    if result is None:
        return {'reason': 'No such paper'}, status.HTTP_404_NOT_FOUND, {}
    return {'document': result}, status.HTTP_200_OK, {}
