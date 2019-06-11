"""Web Server Gateway Interface entry-point."""

from search.factory import create_ui_web_app
import os


__flask_app__ = None


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        # In some deployment scenarios (e.g. uWSGI on k8s), uWSGI will pass in
        # the hostname as part of the request environ. This will usually just
        # be a container ID, which is not helpful for things like building
        # URLs. We want to keep ``SERVER_NAME`` explicitly configured, either
        # in config.py or via an os.environ var loaded by config.py.
        if key == 'SERVER_NAME':
            continue
        os.environ[key] = str(value)
    global __flask_app__
    if __flask_app__ is None:
        __flask_app__ = create_ui_web_app()

    return __flask_app__(environ, start_response)
