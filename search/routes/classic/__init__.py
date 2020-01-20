"""Provides the classic search API."""

from flask import Blueprint, make_response, request, Response

from arxiv.base import logging
from arxiv.users.auth import scopes
from arxiv.users.auth.decorators import scoped
from search import serialize
from search.controllers import classic
from search.routes.consts import ATOM_XML
from search.routes.classic import exceptions

logger = logging.getLogger(__name__)

blueprint = Blueprint('classic', __name__, url_prefix='/classic')


@blueprint.route('/query', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def query() -> Response:
    """Main query endpoint."""
    logger.debug('Got query: %s', request.args)
    data, status_code, headers = classic.query(request.args)
    # requested = request.accept_mimetypes.best_match([JSON, ATOM_XML])
    # if requested == ATOM_XML:
    #     return serialize.as_atom(data), status, headers
    response_data = serialize.as_atom(data['results'], query=data['query'])
    headers.update({'Content-type': ATOM_XML})
    response: Response = make_response(response_data, status_code, headers)
    return response


@blueprint.route('/<arxiv:paper_id>v<string:version>', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    data, status_code, headers = classic.paper(f'{paper_id}v{version}')
    response_data = serialize.as_atom(data['results'])
    headers.update({'Content-type': ATOM_XML})
    response: Response = make_response(response_data, status_code, headers)
    return response
