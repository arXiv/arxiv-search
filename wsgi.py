"""Web Server Gateway Interface entry-point."""

from search.factory import create_ui_web_app
import os


__flask_app__ = create_ui_web_app()


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        if key == 'SERVER_NAME':
            continue
        os.environ[key] = str(value)
        __flask_app__.config[key] = str(value)
    return __flask_app__(environ, start_response)
