"""Search controllers."""

from typing import Tuple, Dict, Any
from search import status, forms, logging
from search.converter import ArXivConverter
from search.process import query
from search.services import index, fulltext, metadata
import search.util as util
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

    response_data = {}
    if request_params.get('advanced', 'false') == 'true':
        logger.debug('search request from advanced form')
        form = forms.AdvancedSearchForm(request_params)
        if form.validate():
            logger.debug('form is valid')
            q = query.from_form(form)
        else:
            logger.debug('form is invalid: %s' % str(form.errors))
            q = None
        response_data['form'] = form
    elif 'query' in request_params:
        try:
            # first check if the URL includes an arXiv ID
            logger.debug(request_params['query'])
            arxiv_id = util.parse_arxiv_id(request_params['query'])
            # If so, redirect.
            logger.debug(arxiv_id)
            return {}, status.HTTP_301_MOVED_PERMANENTLY,\
                {'Location': f'https://arxiv.org/abs/{arxiv_id}'}
            logger.debug("WHY AM I HERE")
                # TODO: use URL constructor to generate URL
                #{'Location': external_url_builder('browse', 'abstract', arxiv_id=arxiv_id)}

        except ValueError as e:
            # If it does not contain an arxiv ID, then parse the query as usual
            q = query.prepare(request_params)
            response_data['query'] = request_params['query']
            response_data['form'] = forms.AdvancedSearchForm()
    else:
        q = None
        response_data['form'] = forms.AdvancedSearchForm()
    if q is not None:
        q = query.paginate(q, request_params)
        response_data.update(index.search(q))
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
