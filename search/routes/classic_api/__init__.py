"""Provides the classic search API."""

__all__ = ["blueprint", "exceptions"]

from flask import Blueprint, make_response, request, Response

import logging


# from arxiv.users.auth import scopes
# from arxiv.users.auth.decorators import scoped
from search import serialize
from search.controllers import classic_api
from search.routes.consts import ATOM_XML
from search.routes.classic_api import exceptions

logger = logging.getLogger(__name__)

blueprint = Blueprint("classic_api", __name__, url_prefix="/")


@blueprint.route("query", methods=["GET"])
# @scoped(required=scopes.READ_PUBLIC)
def query() -> Response:
    """Provide the main query endpoint."""
    logger.debug("Got query: %s", request.args)
    data, status_code, headers = classic_api.query(request.args)
    response_data = serialize.as_atom(  # type: ignore
        data.results, query=data.query
    )  # type: ignore
    headers.update({"Content-type": ATOM_XML})
    response: Response = make_response(response_data, status_code, headers)
    return response


@blueprint.route("<arxiv:paper_id>v<string:version>", methods=["GET"])
# @scoped(required=scopes.READ_PUBLIC)
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    data, status_code, headers = classic_api.paper(f"{paper_id}v{version}")
    response_data = serialize.as_atom(data.results)  # type:ignore
    headers.update({"Content-type": ATOM_XML})
    response: Response = make_response(response_data, status_code, headers)
    return response
