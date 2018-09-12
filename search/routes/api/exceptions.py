"""
Exception handlers for API endpoints.

.. todo:: This module belongs in :mod:`arxiv.base`.

"""

from typing import Callable, List, Tuple

from werkzeug.exceptions import NotFound, Forbidden, Unauthorized, \
    MethodNotAllowed, RequestEntityTooLarge, BadRequest, InternalServerError, \
    HTTPException
from flask import make_response, Response, jsonify

from arxiv import status
from arxiv.base import logging

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


@handler(NotFound)
def handle_not_found(error: NotFound) -> Response:
    """Render the base 404 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_404_NOT_FOUND
    return response


@handler(Forbidden)
def handle_forbidden(error: Forbidden) -> Response:
    """Render the base 403 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_403_FORBIDDEN
    return response


@handler(Unauthorized)
def handle_unauthorized(error: Unauthorized) -> Response:
    """Render the base 401 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_401_UNAUTHORIZED
    return response


@handler(MethodNotAllowed)
def handle_method_not_allowed(error: MethodNotAllowed) -> Response:
    """Render the base 405 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    return response


@handler(RequestEntityTooLarge)
def handle_request_entity_too_large(error: RequestEntityTooLarge) -> Response:
    """Render the base 413 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    return response


@handler(BadRequest)
def handle_bad_request(error: BadRequest) -> Response:
    """Render the base 400 error page."""
    rendered = jsonify({'code': error.code, 'error': error.description})
    response = make_response(rendered)
    response.status_code = status.HTTP_400_BAD_REQUEST
    return response


@handler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    """Render the base 500 error page."""
    if isinstance(error, HTTPException):
        rendered = jsonify({'code': error.code, 'error': error.description})
    else:
        logger.error('Caught unhandled exception: %s', error)
        rendered = jsonify({'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'error': 'Unexpected error'})
    response = make_response(rendered)
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return response
