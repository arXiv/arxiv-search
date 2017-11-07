"""Application factory for references service components."""

import logging
from flask import Flask
from search import routes
from search.services import index


def create_web_app() -> Flask:
    """Initialize an instance of the extractor backend service."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search', static_folder='static', template_folder='templates')
    app.config.from_pyfile('config.py')
    index.init_app(app)

    app.register_blueprint(routes.blueprint)
    return app
