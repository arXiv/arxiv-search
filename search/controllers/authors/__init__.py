"""Controllers for author search."""

from typing import Tuple, Dict, Any, Optional

from werkzeug.exceptions import InternalServerError

from arxiv import status
from search import logging

from search.process import query
from search.services import index, fulltext, metadata
from search.util import parse_arxiv_id
from search.domain import AuthorQuery, Author, AuthorList, Query

from .forms import AuthorSearchForm
# from search.routes.ui import external_url_builder

logger = logging.getLogger(__name__)

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


def search(request_params: dict) -> Response:
    """
    Perform a search based on author name.

    This controller supports both form-based queries from the author search
    form AND requests originating from other parts of the site (e.g. author
    name links on abs page).

    Parameters
    ----------
    request_params : dict

    Returns
    -------
    dict
        Response content.
    int
        HTTP status code.
    dict
        Extra headers to add to the response.
    """
    logger.debug('search request from advanced form')
    response_data = {}
    # This may be a simplified author name query, whih uses ``surname``
    # and ``forename`` parameters instead of the more verbose parameter names
    # used by the AuthorSearchForm.
    request_params = _rewrite_simple_params(request_params)
    form = AuthorSearchForm(request_params)

    query_is_present = 'authors-0-surname' in request_params

    # In some cases, we may want to force the form to be displayed (e.g. if
    # the user wants to revise their query).
    response_data['show_form'] = (
        request_params.get('show_form', False) or not query_is_present
    )

    q: Optional[Query]
    if query_is_present:
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

            response_data['query'] = q
        else:
            logger.debug('form is invalid: %s', str(form.errors))
            q = None
            response_data['query'] = q
            response_data['show_form'] = True
    response_data['form'] = form
    return response_data, status.HTTP_200_OK, {}


def _query_from_form(form: AuthorSearchForm) -> AuthorQuery:
    """
    Generate a :class:`.AuthorQuery` from valid :class:`.AuthorSearchForm`.

    Parameters
    ----------
    form : :class:`.AuthorSearchForm`
        Presumed to be filled and valid.

    Returns
    -------
    :class:`.AuthorQuery`
    """
    q = AuthorQuery(authors=AuthorList([
        Author(
            forename=author['forename'],
            surname=author['surname'],
            fullname=author['fullname']
        )
        for author in form.authors.data
    ]))
    order = form.order.data
    if order and order != 'None':
        q.order = order
    return q


def _rewrite_simple_params(params: dict) -> dict:
    """
    Rewrite simple GET params for :class:`.AuthorSearchForm`.

    Parameters
    ----------
    params : dict
        GET parameters in the request.

    Returns
    -------
    dict
    """
    if 'forename' in params:
        params['authors-0-forename'] = params['forename']
    if 'surname' in params:
        params['authors-0-surname'] = params['surname']
    if 'fullname' in params:
        params['authors-0-fullname'] = params['fullname']
    return params
