"""Provides routing blueprint from the search API."""

from flask import Blueprint, make_response, request, Response

from arxiv.base import logging
from search import serialize
from search.controllers import api

from search.routes.consts import JSON
from search.routes.api import exceptions

from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes

logger = logging.getLogger(__name__)

blueprint = Blueprint('api', __name__, url_prefix='/')


@blueprint.route('/', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def search() -> Response:
    """Main query endpoint."""
    logger.debug('Got query: %s', request.args)
    data, status_code, headers = api.search(request.args)
    # requested = request.accept_mimetypes.best_match([JSON, ATOM_XML])
    # if requested == ATOM_XML:
    #     return serialize.as_atom(data), status, headers
    response_data = serialize.as_json(data['results'], query=data['query'])

    headers.update({'Content-type': JSON})
    response: Response = make_response(response_data, status_code, headers)
    return response


@blueprint.route('/<arxiv:paper_id>v<string:version>', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    data, status_code, headers = api.paper(f'{paper_id}v{version}')
    response_data = serialize.as_json(data['results'])
    headers.update({'Content-type': JSON})
    response: Response = make_response(response_data, status_code, headers)
    return response
