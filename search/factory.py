"""Application factory for references service components."""

import logging

from flask import Flask
from flask_s3 import FlaskS3
from werkzeug.contrib.profiler import ProfilerMiddleware

from arxiv.base import Base
from arxiv.base.middleware import wrap, request_logs
from arxiv.users import auth
from search.routes import ui, api
from search.services import index
from search.converters import ArchiveConverter
from search.encode import ISO8601JSONEncoder

from . import filters

s3 = FlaskS3()


def create_ui_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.config.from_pyfile('config.py')   # type: ignore
    app.url_map.converters['archive'] = ArchiveConverter

    index.SearchSession.init_app(app)

    Base(app)
    app.register_blueprint(ui.blueprint)

    s3.init_app(app)

    wrap(app, [request_logs.ClassicLogsMiddleware])
    # app.config['PROFILE'] = True
    # app.config['DEBUG'] = True
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[100], sort_by=('cumtime', ))

    for filter_name, template_filter in filters.filters:
        app.template_filter(filter_name)(template_filter)

    return app


def create_api_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.json_encoder = ISO8601JSONEncoder
    app.config.from_pyfile('config.py')    # type: ignore

    index.SearchSession.init_app(app)

    Base(app)
    auth.Auth(app)
    app.register_blueprint(api.blueprint)

    wrap(app, [request_logs.ClassicLogsMiddleware,
               auth.middleware.AuthMiddleware])

    for error, handler in api.exceptions.get_handlers():
        app.errorhandler(error)(handler)

    return app


def create_classic_api_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    app = Flask('search')
    app.json_encoder = ISO8601JSONEncoder
    app.config.from_pyfile('config.py')   # type: ignore

    index.SearchSession.init_app(app)

    Base(app)
    auth.Auth(app)
    app.register_blueprint(api.classic.blueprint)

    wrap(app, [request_logs.ClassicLogsMiddleware,
               auth.middleware.AuthMiddleware])

    for error, handler in api.exceptions.get_handlers():
        app.errorhandler(error)(handler)

    return app
