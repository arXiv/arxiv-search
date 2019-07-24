"""Provides the classic search API."""

from flask import Blueprint, make_response, render_template, redirect, \
    request, Response, url_for

from arxiv.base import logging

from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes

from search.controllers import api
from . import serialize, exceptions


logger = logging.getLogger(__name__)

blueprint = Blueprint('api', __name__, url_prefix='/')

ATOM_XML = "application/atom+xml"
JSON = "application/json"


@blueprint.route('/query', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def query() -> Response:
    """Main query endpoint."""
    logger.debug('Got query: %s', request.args)
    data, status_code, headers = api.classic_query(request.args)
    # requested = request.accept_mimetypes.best_match([JSON, ATOM_XML])
    # if requested == ATOM_XML:
    #     return serialize.as_atom(data), status, headers
    response_data = serialize.as_atom(data['results'], query=data['query'])
    headers.update({'Content-type': f'{ATOM_XML}; charset=utf-8'})
    response: Response = make_response(response_data, status_code, headers)
    return response


@blueprint.route('<arxiv:paper_id>v<string:version>', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    # TODO: Investigate if this method should be removed
    data, status_code, headers = api.paper(f'{paper_id}v{version}')
    response_data = serialize.as_atom(data['results'])
    headers.update({'Content-type': f'{ATOM_XML}; charset=utf-8'})
    response: Response = make_response(response_data, status_code, headers)
    return response
