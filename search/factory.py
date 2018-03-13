"""Application factory for references service components."""

import logging

from flask import Flask
from flask_s3 import FlaskS3

from arxiv.base import Base
from search.routes import ui
from search.services import index

s3 = FlaskS3()


def create_ui_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.config.from_pyfile('config.py')

    index.init_app(app)

    Base(app)
    app.register_blueprint(ui.blueprint)

    s3.init_app(app)

    return app
