"""
Handle requests to support the simple search feature.

The primary entrypoint to this module is :func:`.search`, which handles
GET requests to the base search endpoint. It uses :class:`.SimpleSearchForm`
to generate form HTML, validate request parameters, and produce informative
error messages for the user.
"""

from typing import Tuple, Dict, Any, Optional

from werkzeug.exceptions import InternalServerError, NotFound

from arxiv import status
from search import logging

from search.services import index, fulltext, metadata
from search.util import parse_arxiv_id
from search.domain import Query, SimpleQuery, asdict
from search.controllers.util import paginate

from .forms import SimpleSearchForm
# from search.routes.ui import external_url_builder

logger = logging.getLogger(__name__)

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


def search(request_params: dict) -> Response:
    """
    Perform a simple search.

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

    Raises
    ------
    :class:`.InternalServerError`
        Raised when there is a problem communicating with ES, or there was an
        unexpected problem executing the query.
    """
    logger.debug('simple search form')
    response_data = {}  # type: Dict[str, Any]

    logger.debug('simple search request')
    if 'query' in request_params:
        try:
            # first check if the URL includes an arXiv ID
            arxiv_id: Optional[str] = parse_arxiv_id(request_params['query'])
            # If so, redirect.
            logger.debug(f"got arXiv ID: {arxiv_id}")
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
    q: Optional[Query]
    if form.validate():
        logger.debug('form is valid')
        q = _query_from_form(form)
        # Pagination is handled outside of the form.
        q = paginate(q, request_params)
        try:
            # Execute the search. We'll use the results directly in
            #  template rendering, so they get added directly to the
            #  response content.
            response_data.update(asdict(index.search(q)))
        except index.IndexConnectionError as e:
            # There was a (hopefully transient) connection problem. Either
            #  this will clear up relatively quickly (next request), or
            #  there is a more serious outage.
            logger.error('IndexConnectionError: %s', e)
            raise InternalServerError(
                "There was a problem connecting to the search index. This is "
                "quite likely a transient issue, so please try your search "
                "again. If this problem persists, please report it to "
                "help@arxiv.org."
            ) from e
        except index.QueryError as e:
            # Base exception routers should pick this up and show bug page.
            logger.error('QueryError: %s', e)
            raise InternalServerError(
                "There was a problem executing your query. Please try your "
                "search again.  If this problem persists, please report it to "
                "help@arxiv.org."
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
    except index.IndexConnectionError as e:
        # There was a (hopefully transient) connection problem. Either
        #  this will clear up relatively quickly (next request), or
        #  there is a more serious outage.
        logger.error('IndexConnectionError: %s', e)
        raise InternalServerError(
            "There was a problem connecting to the search index. This is "
            "quite likely a transient issue, so please try your search "
            "again. If this problem persists, please report it to "
            "help@arxiv.org."
        ) from e
    except index.QueryError as e:
        # Base exception routers should pick this up and show bug page.
        logger.error('QueryError: %s', e)
        raise InternalServerError(
            "There was a problem executing your query. Please try your "
            "search again.  If this problem persists, please report it to "
            "help@arxiv.org."
        ) from e
    except index.DocumentNotFound as e:
        logger.error('DocumentNotFound: %s', e)
        raise NotFound(f"Could not find a paper with id {document_id}") from e
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
