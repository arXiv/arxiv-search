"""
Exception handlers for API endpoints.

.. todo:: This module belongs in :mod:`arxiv.base`.

"""

from typing import Callable, List, Tuple
from http import HTTPStatus

from werkzeug.exceptions import (
    NotFound,
    Forbidden,
    Unauthorized,
    MethodNotAllowed,
    RequestEntityTooLarge,
    BadRequest,
    InternalServerError,
    HTTPException,
)
from flask import make_response, Response, jsonify

from arxiv.base import logging
from search.routes.consts import JSON

logger = logging.getLogger(__name__)

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


def respond(error: HTTPException, status: HTTPStatus) -> Response:
    """Generate a JSON response."""
    return make_response(  # type: ignore
        jsonify({"code": error.code, "error": error.description}),
        status,
        {"Content-type": JSON},
    )


@handler(NotFound)
def handle_not_found(error: NotFound) -> Response:
    """Render the base 404 error page."""
    return respond(error, HTTPStatus.NOT_FOUND)


@handler(Forbidden)
def handle_forbidden(error: Forbidden) -> Response:
    """Render the base 403 error page."""
    return respond(error, HTTPStatus.FORBIDDEN)


@handler(Unauthorized)
def handle_unauthorized(error: Unauthorized) -> Response:
    """Render the base 401 error page."""
    return respond(error, HTTPStatus.UNAUTHORIZED)


@handler(MethodNotAllowed)
def handle_method_not_allowed(error: MethodNotAllowed) -> Response:
    """Render the base 405 error page."""
    return respond(error, HTTPStatus.METHOD_NOT_ALLOWED)


@handler(RequestEntityTooLarge)
def handle_request_entity_too_large(error: RequestEntityTooLarge) -> Response:
    """Render the base 413 error page."""
    return respond(error, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)


@handler(BadRequest)
def handle_bad_request(error: BadRequest) -> Response:
    """Render the base 400 error page."""
    return respond(error, HTTPStatus.BAD_REQUEST)


@handler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    """Render the base 500 error page."""
    if not isinstance(error, HTTPException):
        logger.error("Caught unhandled exception: %s", error)
        error.code = HTTPStatus.INTERNAL_SERVER_ERROR
    return respond(error, HTTPStatus.INTERNAL_SERVER_ERROR)
