"""Application factory for references service components."""

import logging

from flask import Flask

from arxiv.base import Base
from search.routes import ui
from search.services import index
from search.converter import ArXivConverter
from search import exceptions


def create_ui_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.config.from_pyfile('config.py')
    app.url_map.converters['arxiv'] = ArXivConverter

    index.init_app(app)

    Base(app)
    app.register_blueprint(ui.blueprint)

    # Attach error handlers.
    # TODO: remove this when base exception handling is released in arXiv-base.
    for error, handler in exceptions.get_handlers():
        app.errorhandler(error)(handler)

    return app
