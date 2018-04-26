"""Web Server Gateway Interface entry-point."""

from search.factory import create_ui_web_app
import os


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        if type(value) is str:
            os.environ[key] = value
    app = create_ui_web_app()
    return app(environ, start_response)
