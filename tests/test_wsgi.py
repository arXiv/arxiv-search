"""Tests for ``wsgi.py``."""

from unittest import TestCase, mock
import wsgi


class TestConfigFromEnviron(TestCase):
    """Some deployment environments pass config at request time."""

    @mock.patch(f"{wsgi.__name__}.__flask_app__", mock.MagicMock(config={}))
    def test_config_set_from_environ(self):
        """Some config params are passed on the WSGI environ."""
        wsgi.__flask_app__.config["FOO"] = 1
        wsgi.application({"FOO": 2}, mock.MagicMock())
        self.assertEqual(
            wsgi.__flask_app__.config["FOO"],
            2,
            "App config is updated from environ",
        )
