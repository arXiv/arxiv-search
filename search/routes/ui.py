"""Provides REST API routes."""

from urllib.parse import urljoin

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, url_for

from search import controllers

blueprint = Blueprint('ui', __name__, url_prefix='/search')


@blueprint.route('/', methods=['GET'])
def search():
    """First pass at a search results page."""
    response, code, headers = controllers.search(request.args.to_dict())
    return render_template("search/search.html", **response)


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
def external_url_builder():
    """Add an external URL builder function to the template context."""
    def external_url(service: str, name: str, **parameters) -> str:
        """Build an URL to external endpoint."""
        if service == 'browse':
            return _browse_url(name, **parameters)
        return
    return dict(external_url=external_url)
