"""Provides the main search user interfaces."""

from typing import Dict, Callable, Union, Any, Optional
from functools import wraps
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, Response, \
    url_for
from werkzeug.urls import Href, url_encode, url_parse, url_unparse, url_encode

from arxiv import status
from arxiv.base import logging
from werkzeug.exceptions import InternalServerError
from search.controllers import simple, advanced, health_check

logger = logging.getLogger(__name__)

blueprint = Blueprint('ui', __name__, url_prefix='/')


@blueprint.after_request
def apply_response_headers(response: Response) -> Response:
    """Hook for applying response headers to all responses."""
    """Prevent UI redress attacks"""
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@blueprint.route('/', methods=['GET'])
def search() -> Union[str, Response]:
    """First pass at a search results page."""
    response, code, headers = simple.search(request.args)
    logger.debug(f"controller returned code: {code}")
    if code == status.HTTP_200_OK:
        return render_template(
            "search/search.html",
            pagetitle="Search",
            **response
        )
    elif (code == status.HTTP_301_MOVED_PERMANENTLY
          or code == status.HTTP_303_SEE_OTHER):
        return redirect(headers['Location'], code=code)
    raise InternalServerError('Unexpected error')


@blueprint.route('advanced', methods=['GET'])
def advanced_search() -> Union[str, Response]:
    """Advanced search interface."""
    response, code, headers = advanced.search(request.args)
    return render_template(
        "search/advanced_search.html",
        pagetitle="Advanced Search",
        **response
    )


@blueprint.route('status', methods=['GET', 'HEAD'])
def service_status() -> Union[str, Response]:
    """
    Health check endpoint for search.

    Exercises the search index connection with a real query.
    """
    return health_check()


def _browse_url(name: str, **parameters: Any) -> Optional[str]:
    """Generate a URL for a browse route."""
    paper_id = parameters.get('paper_id')
    if paper_id is None:
        return None
    if name == 'abstract':
        route = 'abs'
    elif name.startswith('pdf'):
        route = 'pdf'
    elif name == 'other':
        route = 'format'
    elif name == 'ps':
        route = 'ps'
    return urljoin('https://arxiv.org', '/%s/%s' % (route, paper_id))


@blueprint.context_processor
def external_url_builder() -> Dict[str, Callable]:
    """Add an external URL builder function to the template context."""
    def external_url(service: str, name: str, **parameters: Any) \
            -> Optional[str]:
        """Build an URL to external endpoint."""
        if service == 'browse':
            return _browse_url(name, **parameters)
        return None
    return dict(external_url=external_url)


@blueprint.context_processor
def url_for_page_builder() -> Dict[str, Callable]:
    """Add a page URL builder function to the template context."""
    def url_for_page(page: int, page_size: int) -> str:
        """Build an URL to for a search result page."""
        rule = request.url_rule
        parts = url_parse(url_for(rule.endpoint))
        args = request.args.copy()
        args['start'] = (page - 1) * page_size
        parts = parts.replace(query=url_encode(args))
        url: str = url_unparse(parts)
        return url
    return dict(url_for_page=url_for_page)


@blueprint.context_processor
def current_url_sans_parameters_builder() -> Dict[str, Callable]:
    """Add a function to strip GET parameters from the current URL."""
    def current_url_sans_parameters(*params_to_remove: str) -> str:
        """Get the current URL with ``param`` removed from GET parameters."""
        rule = request.url_rule
        parts = url_parse(url_for(rule.endpoint))
        args = request.args.copy()
        for param in params_to_remove:
            args.pop(param, None)
        parts = parts.replace(query=url_encode(args))
        url: str = url_unparse(parts)
        return url
    return dict(current_url_sans_parameters=current_url_sans_parameters)


@blueprint.context_processor
def url_for_author_search_builder() -> Dict[str, Callable]:
    """Inject a function to build author name query URLs."""
    def url_for_author_search(forename: str, surname: str) -> str:
        parts = url_parse(url_for('ui.search'))
        parts = parts.replace(query=url_encode({
            'searchtype': 'author',
            'query': f'"{surname}, {forename}"'
        }))
        url: str = url_unparse(parts)
        return url
    return dict(url_for_author_search=url_for_author_search)


@blueprint.context_processor
def url_with_params_builder() -> Dict[str, Callable]:
    """Inject a URL builder that handles GET parameters."""
    def url_with_params(name: str, values: dict, params: dict) -> str:
        """Build a URL for ``name`` with path ``values`` and GET ``params``."""
        parts = url_parse(url_for(name, **values))
        parts = parts.replace(query=url_encode(params))
        url: str = url_unparse(parts)
        return url
    return dict(url_with_params=url_with_params)
