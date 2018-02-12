"""Application factory for references service components."""

import logging

from flask import Flask

from arxiv.base import Base
from search.routes import ui, external_api
from search.services import index
from search.converter import ArXivConverter


def create_web_app() -> Flask:
    """Initialize an instance of the extractor backend service."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.config.from_pyfile('config.py')
    app.url_map.converters['arxiv'] = ArXivConverter

    index.init_app(app)

    Base(app)
    app.register_blueprint(ui.blueprint)
    app.register_blueprint(external_api.blueprint)
    return app
