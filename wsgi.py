"""Web Server Gateway Interface entry-point."""

from search.factory import create_ui_web_app
import os


def application(environ, start_response):
    """WSGI application factory."""
    app = create_ui_web_app()
    return app(environ, start_response)
