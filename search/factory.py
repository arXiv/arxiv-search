"""Application factory for references service components."""

import logging

from flask import Flask
from flask.logging import default_handler
from flask_s3 import FlaskS3

from arxiv.base import Base
from arxiv.base.middleware import wrap, request_logs
from search.routes import ui, api, classic_api
from search.services import index
from search.converters import ArchiveConverter
from search.encode import ISO8601JSONEncoder

from search.domain.base import SimpleQuery

from . import filters

s3 = FlaskS3()

def create_ui_web_app(skip_startup_check=False) -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    root = logging.getLogger()
    root.addHandler(default_handler)

    logging.getLogger("boto").setLevel(logging.ERROR)
    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    app = Flask("search")
    app.config.from_pyfile("config.py")  # type: ignore
    app.url_map.converters["archive"] = ArchiveConverter

    index.SearchSession.init_app(app)

    Base(app)
    app.register_blueprint(ui.blueprint)

    s3.init_app(app)

    wrap(app, [request_logs.ClassicLogsMiddleware])
    # app.config['PROFILE'] = True
    # app.config['DEBUG'] = True
    # app.wsgi_app = ProfilerMiddleware(
    #     app.wsgi_app, restrictions=[100], sort_by=('cumtime', )
    # )

    for filter_name, template_filter in filters.filters:
        app.template_filter(filter_name)(template_filter)

    if not skip_startup_check:
        index_startup_check(app)

    return app


def create_api_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    root = logging.getLogger()
    root.addHandler(default_handler)

    logging.getLogger("boto").setLevel(logging.ERROR)
    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    app = Flask("search")
    app.json_encoder = ISO8601JSONEncoder
    app.config.from_pyfile("config.py")  # type: ignore

    index.SearchSession.init_app(app)

    Base(app)
    app.register_blueprint(api.blueprint)
    wrap(
        app, [request_logs.ClassicLogsMiddleware],
    )

    for error, handler in api.exceptions.get_handlers():
        app.errorhandler(error)(handler)

    return app


def create_classic_api_web_app() -> Flask:
    """Initialize an instance of the search frontend UI web application."""
    root = logging.getLogger()
    root.addHandler(default_handler)

    logging.getLogger("boto").setLevel(logging.ERROR)
    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)

    app = Flask("search")
    app.json_encoder = ISO8601JSONEncoder
    app.config.from_pyfile("config.py")  # type: ignore

    index.SearchSession.init_app(app)

    Base(app)
    app.register_blueprint(classic_api.blueprint)
    wrap(
        app, [request_logs.ClassicLogsMiddleware],
    )

    for error, handler in classic_api.exceptions.get_handlers():
        app.errorhandler(error)(handler)

    return app


def index_startup_check(app):
    """Raises if there is a problem with the service."""
    logging.info("********* Startup service check for ES **************")
    search_service = index.SearchSession.get_session(app)
    if search_service.cluster_available():
        logging.info("Startup service check: ES cluster is available")
    else:
        raise Exception("Startup service check: ABORTING STARTUP: ES cluster is not available at " +
                        app.config["ELASTICSEARCH_SERVICE_HOST"] + ":" +
                        str(app.config["ELASTICSEARCH_SERVICE_PORT"])
                        )
    try:
        if search_service.index_exists(app.config["ELASTICSEARCH_INDEX"]):
            logging.info("ES index is available")
        else:
            raise Exception("Index does not exist")
    except Exception as ex:
        logging.error("Startup service check: ABORTING STARTUP: " +
                      app.config["ELASTICSEARCH_SERVICE_HOST"] + ":" +
                      str(app.config["ELASTICSEARCH_SERVICE_PORT"]) + " index " +
                      app.config["ELASTICSEARCH_INDEX"] + "' is not available")
        raise ex

    try:
        document_set = index.SearchSession.search(  # type: ignore
            SimpleQuery(search_field="all", value="theory")
        )
        if document_set["results"]:
            logging.info("ES index successfully returned results for a test search")
        else:
            raise Exception("ES index failed to return results for a test search")
    except Exception as ex:
        logging.error("Startup service check: ABORTING STARTUP: ES at" +
                      app.config["ELASTICSEARCH_SERVICE_HOST"] + ":" +
                      str(app.config["ELASTICSEARCH_SERVICE_PORT"]) + " index " +
                      app.config["ELASTICSEARCH_INDEX"] + " failed to handle a simple search.")
                          
        raise ex
    
    logging.info("********* Startup service check for ES Successful! **************")                      

            
        
    
