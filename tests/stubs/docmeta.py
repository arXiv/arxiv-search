"""Stub for the docmeta service."""
import os
import json
from flask import Flask
from flask.json import jsonify
from werkzeug.exceptions import NotFound, InternalServerError

from arxiv.base import Base
from arxiv.base.converter import ArXivConverter
from arxiv.base import logging

logger = logging.getLogger(__name__)

METADATA_DIR = os.environ.get("METADATA_DIR")


app = Flask("metadata")
Base(app)

app.url_map.converters["arxiv"] = ArXivConverter


@app.route("/docmeta/<arxiv:document_id>", methods=["GET"])
def docmeta(document_id):
    """Retrieve document metadata."""
    logger.debug(f"Get metadata for {document_id}")
    logger.debug(f"Metadata base is {METADATA_DIR}")
    if not METADATA_DIR:
        raise InternalServerError("Metadata directory not set")
    metadata_path = os.path.join(METADATA_DIR, f"{document_id}.json")
    logger.debug(f"Metadata path is {metadata_path}")
    if not os.path.exists(metadata_path):
        raise NotFound("No such document")
    with open(metadata_path) as f:
        return jsonify(json.load(f))


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        os.environ[key] = str(value)
    return app(environ, start_response)
