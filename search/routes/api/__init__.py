"""Provides routing blueprint from the search API."""

import json
from typing import Dict, Callable, Union, Any, Optional, List
from functools import wraps
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, Response, \
    url_for
from werkzeug.urls import Href, url_encode, url_parse, url_unparse, url_encode
from werkzeug.datastructures import MultiDict, ImmutableMultiDict

from arxiv import status
from arxiv.base import logging
from werkzeug.exceptions import InternalServerError
from search.controllers import api

from . import serialize

# from arxiv.users.auth.decorators import scoped
# from arxiv.users.auth import scopes

logger = logging.getLogger(__name__)

blueprint = Blueprint('api', __name__, url_prefix='/')

ATOM_XML = "application/atom+xml"
JSON = "application/json"


# @scoped(scopes.READ_API)
@blueprint.route('/', methods=['GET'])
def search() -> Response:
    """Main query endpoint."""
    data, status_code, headers = api.search(request.args)
    # requested = request.accept_mimetypes.best_match([JSON, ATOM_XML])
    # if requested == ATOM_XML:
    #     return serialize.as_atom(data), status, headers
    return serialize.as_json(data), status_code, headers


@blueprint.route('<arxiv:paper_id>v<string:version>', methods=['GET'])
def paper(paper_id: str, version: str) -> Response:
    """Document metadata endpoint."""
    data, status_code, headers = api.paper(f'{paper_id}v{version}')
    return serialize.as_json(data), status_code, headers
