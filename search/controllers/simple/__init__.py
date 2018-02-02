"""Search controllers."""

from typing import Tuple, Dict, Any
from arxiv import status
from search import logging

from search.process import query
from search.services import index, fulltext, metadata
from search.util import parse_arxiv_id
from search.domain import SimpleQuery

from .forms import SimpleSearchForm
# from search.routes.ui import external_url_builder

logger = logging.getLogger(__name__)

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
    logger.debug('simple search form')
    response_data = {}

    logger.debug('simple search request')
    if 'value' in request_params:
        try:
            # first check if the URL includes an arXiv ID
            logger.debug('!! %s', request_params['value'])
            arxiv_id = parse_arxiv_id(request_params['value'])
            logger.debug('foo')
            # If so, redirect.
            logger.debug(arxiv_id)
        except ValueError as e:
            logger.debug('No arXiv ID detected; fall back to form')
            arxiv_id = None
    else:
        arxiv_id = None

    if arxiv_id:
        return {}, status.HTTP_301_MOVED_PERMANENTLY,\
            {'Location': f'https://arxiv.org/abs/{arxiv_id}'}
        logger.debug("WHY AM I HERE")
        # TODO: use URL constructor to generate URL
        #{'Location': external_url_builder('browse', 'abstract', arxiv_id=arxiv_id)}

    # Fall back to form-based search.
    form = SimpleSearchForm(request_params)
    if form.validate():
        logger.debug('form is valid')
        q = _query_from_form(form)
        q = query.paginate(q, request_params)
        response_data.update(index.search(q))
        response_data['query'] = q
    else:
        logger.debug('form is invalid: %s' % str(form.errors))
        q = None
        response_data['query'] = q
    response_data['form'] = form
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


def _query_from_form(form: SimpleSearchForm) -> SimpleQuery:
    """
    Generate a :class:`.SimpleQuery` from valid :class:`.SimpleSearchForm`.

    Parameters
    ----------
    form : :class:`.SimpleSearchForm`
        Presumed to be filled and valid.

    Returns
    -------
    :class:`.SimpleQuery`
    """
    query = SimpleQuery()
    query.field = form.searchtype.data
    query.value = form.query.data
    return query
