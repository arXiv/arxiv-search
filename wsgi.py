"""Web Server Gateway Interface entry-point for UI."""

import os

__flask_app__ = None


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        # Copy string WSGI environ to os.environ. This is to get apache
        # SetEnv vars.  It needs to be done before the call to
        # create_web_app() due to how config is setup from os in
        # search/config.py.
        #
        # In some deployment scenarios (e.g. uWSGI on k8s), uWSGI will pass in
        # the hostname as part of the request environ. This will usually just
        # be a container ID, which is not helpful for things like building
        # URLs. We want to keep ``SERVER_NAME`` explicitly configured, either
        # in config.py or via an os.environ var loaded by config.py.
        if key == "SERVER_NAME":
            continue
        if type(value) is str:
            os.environ[key] = value

    global __flask_app__
    if __flask_app__ is None:
        from search.factory import create_ui_web_app
        __flask_app__ = create_ui_web_app()

    return __flask_app__(environ, start_response)
