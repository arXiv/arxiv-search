"""Search controllers."""

from typing import Tuple, Dict, Any

from werkzeug.exceptions import InternalServerError, NotFound

from arxiv import status
from search import logging

from search.process import query
from search.services import index, fulltext, metadata
from search.util import parse_arxiv_id
from search.domain import Query, SimpleQuery

from .forms import SimpleSearchForm
# from search.routes.ui import external_url_builder

logger = logging.getLogger(__name__)

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


def health() -> Response:
    """Check integrations."""
    return {'index': index.ok()}, status.HTTP_200_OK, {}


def search(request_params: dict) -> Response:
    """
    Perform a simple search using a single parameter.

    This supports requests from both the form-based view (provided here) AND
    from the mini search widget displayed on all arXiv.org pages.

    At a minimum, expects the parameter ``value`` in the GET request. This may
    be a match value for a search query, or an arXiv ID.

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
    response_data = {} # type: Dict[str, Any]

    logger.debug('simple search request')
    if 'query' in request_params:
        try:
            # first check if the URL includes an arXiv ID
            arxiv_id = parse_arxiv_id(request_params['query'])
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
        # TODO: use URL constructor to generate URL
        #{'Location': external_url_builder('browse', 'abstract', arxiv_id=arxiv_id)}

    # Fall back to form-based search.
    form = SimpleSearchForm(request_params)
    q: Query
    if form.validate():
        logger.debug('form is valid')
        q = _query_from_form(form)
        # Pagination is handled outside of the form.
        q = query.paginate(q, request_params)
        try:
            # Execute the search. We'll use the results directly in
            #  template rendering, so they get added directly to the
            #  response content.
            response_data.update(index.search(q))
        except index.IndexConnectionError as e:
            # There was a (hopefully transient) connection problem. Either
            #  this will clear up relatively quickly (next request), or
            #  there is a more serious outage.
            response_data['index_error'] = True
        except index.QueryError as e:
            # Base exception routers should pick this up and show bug page.
            raise InternalServerError(
                'Encountered an error in search query'
            ) from e
    else:
        logger.debug('form is invalid: %s', str(form.errors))
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

    Raises
    ------
    InternalServerError
        Encountered error in search query.
    NotFound
        No such document
    """
    try:
        result = index.get_document(document_id)
    except index.QueryError as e:
        # Base exception routers should pick this up and show bug page.
        raise InternalServerError('Encountered error in search query') from e
    except index.IndexConnectionError as e:
        return {'index_error': True}, status.HTTP_200_OK, {}
    except index.DocumentNotFound as e:
        # Base exception routers should pick this up and show 404 not found.
        raise NotFound('No such document')
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
    q = SimpleQuery()
    q.field = form.searchtype.data
    q.value = form.query.data
    order = form.order.data
    if order and order != 'None':
        q.order = order
    return q
