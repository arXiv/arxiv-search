"""Provides REST API routes."""

from functools import wraps

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, url_for

from search import controllers

blueprint = Blueprint('external_api', __name__, url_prefix='/search/api')


def json_response(func):
    """Generate a wrapper for routes that JSONifies the response body."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        r_body, r_status, r_headers = func(*args, **kwargs)
        return jsonify(r_body), r_status, r_headers
    return wrapper


@blueprint.route('/', methods=['GET'])
@json_response
def search():
    """First pass at a search results page."""
    return controllers.search(request.args.to_dict())


@blueprint.route('/<arxiv:document_id>', methods=['GET'])
@json_response
def retrieve_document(document_id):
    """Retrieve an arXiv paper by ID."""
    return controllers.retrieve_document(document_id)


@blueprint.route('/status', methods=['GET'])
@json_response
def ok():
    """Health check endpoint."""
    return controllers.health()
