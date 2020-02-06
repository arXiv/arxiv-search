"""Provides the main search user interfaces."""

import json
from typing import Dict, Callable, Union, Any, Optional, List
from functools import wraps
from functools import lru_cache as memoize


from flask.json import jsonify
from flask import (
    Blueprint,
    render_template,
    redirect,
    request,
    Response,
    url_for,
    make_response,
)
from werkzeug.urls import Href
from werkzeug.datastructures import MultiDict, ImmutableMultiDict
from werkzeug.wrappers import Response as WerkzeugResponse

from arxiv import status
from arxiv.base import logging
from werkzeug.exceptions import InternalServerError
from search.controllers import simple, advanced, health_check

from . import context_processors

_Response = Union[Response, WerkzeugResponse]

logger = logging.getLogger(__name__)

blueprint = Blueprint("ui", __name__, url_prefix="/")

PARAMS_TO_PERSIST = ["order", "size", "abstracts", "date-date_type"]
"""These parameters should be persisted in a cookie."""

PARAMS_COOKIE_NAME = "arxiv-search-parameters"
"""The name of the cookie to use to persist search parameters."""


@blueprint.before_request
def get_parameters_from_cookie() -> None:
    """
    Use parameter values in a cookie as defaults if not explicitly provided.

    This will replace request.args with a :class:`.MultiDict` in order to
    achieve mutability.
    """
    # If the cookie is not set, there is nothing to do.
    if PARAMS_COOKIE_NAME not in request.cookies:
        return

    # We need the request args to be mutable.
    request.args = MultiDict(request.args.items(multi=True))  # type: ignore
    data = json.loads(request.cookies[PARAMS_COOKIE_NAME])
    for param in PARAMS_TO_PERSIST:
        # Don't clobber the user's explicit request.
        if param not in request.args and param in data:
            request.args[param] = data[param]
    # ``request`` is a proxy object; there is nothing to return.


@blueprint.after_request
def set_parameters_in_cookie(response: Response) -> Response:
    """Set request parameters in the cookie, to use as future defaults."""
    if response.status_code == status.HTTP_200_OK:
        data = {
            param: request.args[param]
            for param in PARAMS_TO_PERSIST
            if param in request.args
        }
        response.set_cookie(PARAMS_COOKIE_NAME, json.dumps(data))
    return response


@blueprint.after_request
def apply_response_headers(response: Response) -> Response:
    """Hook for applying response headers to all responses."""
    """Prevent UI redress attacks"""
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@blueprint.route("<archive:archives>", methods=["GET"])
@blueprint.route("/", methods=["GET"])
def search(archives: Optional[List[str]] = None) -> _Response:
    """Simple search interface."""
    data, code, hdrs = simple.search(request.args, archives)
    logger.debug(f"controller returned code: {code}")
    if code == status.HTTP_200_OK:
        content = render_template(
            "search/search.html", pagetitle="Search", archives=archives, **data
        )
        response: Response = make_response(content)
        for key, value in hdrs.items():
            response.headers[key] = value
        return response
    elif (
        code == status.HTTP_301_MOVED_PERMANENTLY
        or code == status.HTTP_303_SEE_OTHER
    ):
        return redirect(hdrs["Location"], code=code)
    raise InternalServerError("Unexpected error")


@blueprint.route("advanced", methods=["GET"])
def advanced_search() -> _Response:
    """Advanced search interface."""
    data, code, hdrs = advanced.search(request.args)
    content = render_template(
        "search/advanced_search.html", pagetitle="Advanced Search", **data
    )
    response: Response = make_response(content)
    response.status_code = code
    for key, value in hdrs.items():
        response.headers[key] = value
    return response


@blueprint.route("advanced/<string:groups_or_archives>", methods=["GET"])
def group_search(groups_or_archives: str) -> _Response:
    """
    Short-cut for advanced search with group or archive pre-selected.

    Note that this only supports options supported in the advanced search
    interface. Anything else will result in a 404.
    """
    data, code, hdrs = advanced.group_search(request.args, groups_or_archives)
    content = render_template(
        "search/advanced_search.html", pagetitle="Advanced Search", **data
    )
    response: Response = make_response(content)
    response.status_code = code
    for key, value in hdrs.items():
        response.headers[key] = value
    return response


@blueprint.route("status", methods=["GET", "HEAD"])
def service_status() -> _Response:
    """
    Health check endpoint for search.

    Exercises the search index connection with a real query.
    """
    content, code, hdrs = health_check()
    response: Response = make_response(content)
    response.status_code = code
    for key, value in hdrs.items():
        response.headers[key] = value
    return response


# Register context processors.
for context_processor in context_processors.context_processors:
    blueprint.context_processor(context_processor)
