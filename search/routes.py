"""Provides REST API routes."""

from flask.json import jsonify
from flask import Blueprint, render_template, redirect, request, url_for

from search import controllers

blueprint = Blueprint('search', __name__, url_prefix='')


# TODO: remove this before first release.
@blueprint.route('/ack', methods=['GET'])
def ack():
    """This is an example of template rendering."""
    return render_template("ack.html")


@blueprint.route('/searchresults', methods=['GET'])
def searchresults():
    """First pass at a search results page."""
    response, code, headers = controllers.search(**request.args.to_dict())
    return render_template("search/search-results.html", **response['results'])


@blueprint.route('/status', methods=['GET'])
def ok():
    """Health check endpoint."""
    response, code, headers = controllers.health()
    return jsonify(response), code, headers


@blueprint.route('/find', methods=['GET'])
def find():
    """Search endpoint."""
    response, code, headers = controllers.search(**request.args.to_dict())
    return jsonify(response), code, headers
