"""Provides REST API routes."""

from typing import Dict, Callable
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, url_for
from werkzeug.urls import Href, url_encode
from search.controllers import simple, advanced
from arxiv import status

from search import logging

logger = logging.getLogger(__name__)

blueprint = Blueprint('ui', __name__, url_prefix='/search')


@blueprint.route('/', methods=['GET'])
def search():
    """First pass at a search results page."""
    response, code, headers = simple.search(request.args)
    logger.debug(code)
    if code == status.HTTP_200_OK:
        return render_template("search/search.html", **response)
    elif (code == status.HTTP_301_MOVED_PERMANENTLY
          or code == status.HTTP_303_SEE_OTHER):
        return redirect(headers['Location'], code=code)


@blueprint.route('/advanced', methods=['GET'])
def advanced_search():
    """Advanced search interface."""
    response, code, headers = advanced.search(request.args)
    return render_template("search/advanced_search.html", **response)


# TODO: we need something more robust here; this is just to get us rolling.
def _browse_url(name, **parameters):
    paper_id = parameters.get('paper_id')
    if paper_id is None:
        return
    if name == 'abstract':
        route = 'abs'
    elif name == 'pdf':
        route = 'pdf'
    return urljoin('https://arxiv.org', '/%s/%s' % (route, paper_id))


# TODO: we need something more robust here; this is just to get us rolling.
@blueprint.context_processor
def external_url_builder() -> Dict[str, Callable]:
    """Add an external URL builder function to the template context."""
    def external_url(service: str, name: str, **parameters) -> str:
        """Build an URL to external endpoint."""
        if service == 'browse':
            return _browse_url(name, **parameters)
        return
    return dict(external_url=external_url)


@blueprint.context_processor
def url_for_page_builder() -> Dict[str, Callable]:
    """Add a page URL builder function to the template context."""
    def url_for_page(page: int, page_size: int) -> str:
        """Build an URL to for a search result page."""
        href = Href('/')
        args = request.args.copy()
        args['start'] = (page - 1) * page_size
        return href(request.path, args)
    return dict(url_for_page=url_for_page)


@blueprint.context_processor
def current_url_sans_parameter_builder() -> Dict[str, Callable]:
    """Add a function to strip GET parameters from the current URL."""
    def current_url_sans_parameter(param: str) -> str:
        """Get the current URL with ``param`` removed from GET parameters."""
        scheme, netloc, path, params, query, fragment = urlparse(request.path)
        query_params = request.args.copy()
        query_params.pop(param, None)
        query = url_encode(query_params)
        return urlunparse((scheme, netloc, path, params, query, fragment))
    return dict(current_url_sans_parameter=current_url_sans_parameter)
