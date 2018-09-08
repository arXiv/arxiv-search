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

# from arxiv.users.auth.decorators import scoped
# from arxiv.users.auth import scopes

logger = logging.getLogger(__name__)

blueprint = Blueprint('api', __name__, url_prefix='/')


# @scoped(scopes.READ_API)
@blueprint.route('/', methods=['GET'])
def search() -> Response:
    data, status, headers = api.search(request.args)
    return jsonify(data), status, headers
