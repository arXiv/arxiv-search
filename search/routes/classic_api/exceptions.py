"""
Exception handlers for classic arXiv API endpoints.

.. todo:: This module belongs in :mod:`arxiv.base`.

"""
from http import HTTPStatus
from typing import Callable, List, Tuple
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
from flask import make_response, Response

import logging

from search.serialize import as_atom
from search.domain import Error
from search.routes.consts import ATOM_XML
from search.errors import ValidationError


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
    """Get a list of registered exception handlers.

    Returns
    -------
    list
        List of (:class:`.HTTPException`, callable) tuples.

    """
    return _handlers


def respond(
    error_msg: str,
    link: str = "https://arxiv.org/api/errors",
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
) -> Response:
    """Generate an Atom response."""
    return make_response(  # type: ignore
        as_atom(Error(id=link, error=error_msg, link=link)),
        status,
        {"Content-type": ATOM_XML},
    )


@handler(NotFound)
def handle_not_found(error: NotFound) -> Response:
    """Render the base 404 error page."""
    return respond(error.description, status=HTTPStatus.NOT_FOUND)


@handler(Forbidden)
def handle_forbidden(error: Forbidden) -> Response:
    """Render the base 403 error page."""
    return respond(error.description, status=HTTPStatus.FORBIDDEN)


@handler(Unauthorized)
def handle_unauthorized(error: Unauthorized) -> Response:
    """Render the base 401 error page."""
    return respond(error.description, status=HTTPStatus.UNAUTHORIZED)


@handler(MethodNotAllowed)
def handle_method_not_allowed(error: MethodNotAllowed) -> Response:
    """Render the base 405 error page."""
    return respond(error.description, status=HTTPStatus.METHOD_NOT_ALLOWED)


@handler(RequestEntityTooLarge)
def handle_request_entity_too_large(error: RequestEntityTooLarge) -> Response:
    """Render the base 413 error page."""
    return respond(
        error.description, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    )


@handler(BadRequest)
def handle_bad_request(error: BadRequest) -> Response:
    """Render the base 400 error page."""
    return respond(error.description, status=HTTPStatus.BAD_REQUEST)


@handler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    """Render the base 500 error page."""
    if not isinstance(error, HTTPException):
        logger.error("Caught unhandled exception: %s", error)
    return respond(error.description, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@handler(ValidationError)
def handle_validation_error(error: ValidationError) -> Response:
    """Render the base 400 error page."""
    return respond(
        error_msg=error.message, link=error.link, status=HTTPStatus.BAD_REQUEST
    )
