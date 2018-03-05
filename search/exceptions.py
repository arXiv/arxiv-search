"""
Handling of HTTP exceptions.

This functionality should be incorporated into arXiv-base in a future release,
at which time much (if not all) of this module should be removed.
"""

from typing import Callable, List, Tuple

from werkzeug.exceptions import NotFound, Forbidden, Unauthorized, \
    MethodNotAllowed, RequestEntityTooLarge, BadRequest, InternalServerError, \
    HTTPException
from flask import render_template, make_response, Response

from arxiv import status

_handlers = []


def handler(exception: type) -> Callable:
    """Generate a decorator to register a handler for an exception."""
    def deco(func: Callable) -> Callable:
        """Register a function as an exception handler."""
        _handlers.append((exception, func))
        return func
    return deco


def get_handlers() -> List[Tuple[type, Callable]]:
    """
    Get a list of registered exception handlers.

    Returns
    -------
    list
        List of (:class:`.HTTPException`, callable) tuples.

    """
    return _handlers


@handler(NotFound)
def handle_not_found(error: NotFound) -> Response:
    """Render the base 404 error page."""
    context = dict(error=error, pagetitle="Page not found")
    response = make_response(render_template("search/404.html", **context))
    response.status_code = status.HTTP_404_NOT_FOUND
    return response


@handler(MethodNotAllowed)
def handle_method_not_allowed(error: MethodNotAllowed) -> Response:
    """Render the base 405 error page."""
    context = dict(error=error, pagetitle="Method not allowed")
    response = make_response(render_template("search/405.html", **context))
    response.status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    return response


@handler(HTTPException)
@handler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    """Render the base 500 error page."""
    context = dict(error=error, pagetitle="Whoops!")
    response = make_response(render_template("search/500.html", **context))
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response
