"""Provides the classic search API."""

from flask import Blueprint, render_template, redirect, request, Response, \
    url_for

from arxiv.base import logging
from search.controllers import api

from . import serialize, exceptions

from arxiv.users.auth.decorators import scoped
from arxiv.users.auth import scopes

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
    response = serialize.as_json(data['results'], query=data['query'])
    response.status_code = status_code
    response.headers.extend(headers)
    return response


@blueprint.route('<arxiv:paper_id>v<string:version>', methods=['GET'])
@scoped(required=scopes.READ_PUBLIC)
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    data, status_code, headers = api.paper(f'{paper_id}v{version}')
    response = serialize.as_json(data['results'])
    response.status_code = status_code
    response.headers.extend(headers)
    return response
