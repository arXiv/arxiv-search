"""Tests related to the persistence of search parameters in a cookie."""

import json
from unittest import TestCase, mock

from search.factory import create_ui_web_app
from search.controllers.simple.forms import SimpleSearchForm
from search.routes import ui


class TestParameterPersistence(TestCase):
    """Some search parameters should be saved in a cookie."""

    def setUp(self):
        """Instantiate the UI application."""
        self.app = create_ui_web_app()
        self.client = self.app.test_client()

    def test_request_includes_params(self):
        """A request is made with parameters indicated for persistence."""
        ui.PARAMS_TO_PERSIST = ["foo", "baz"]
        ui.PARAMS_COOKIE_NAME = "foo-cookie"
        response = self.client.get("/?foo=bar&baz=bat")

        self.assertIn("Set-Cookie", response.headers, "Should set a cookie")
        expected = (
            'foo-cookie="{\\"foo\\": \\"bar\\"\\054 \\"baz\\": \\"bat\\"}"; '
            "Path=/"
        )
        self.assertEqual(
            response.headers["Set-Cookie"],
            expected,
            "Cookie should contain request params",
        )

    def test_request_does_not_include_params(self):
        """The request does not include persistable params."""
        ui.PARAMS_TO_PERSIST = ["foo", "baz"]
        ui.PARAMS_COOKIE_NAME = "foo-cookie"
        response = self.client.get("/?nope=nope")
        self.assertIn("Set-Cookie", response.headers, "Should set a cookie")
        self.assertEqual(
            response.headers["Set-Cookie"],
            'foo-cookie="{}"; Path=/',
            "Cookie should not contain request params",
        )

    @mock.patch("search.routes.ui.simple")
    def test_request_includes_cookie(self, mock_simple):
        """The request includes the params cookie."""
        mock_simple.search.return_value = {'form': SimpleSearchForm()}, 200, {}
        ui.PARAMS_TO_PERSIST = ['foo', 'baz']
        ui.PARAMS_COOKIE_NAME = 'foo-cookie'
        self.client.set_cookie('', ui.PARAMS_COOKIE_NAME,
                               json.dumps({'foo': 'ack'}))
        self.client.get('/')
        self.assertEqual(mock_simple.search.call_args[0][0]['foo'], 'ack',
                         'The value in the cookie should be used')

    @mock.patch('search.routes.ui.simple')
    def test_request_includes_cookie_but_also_explicit_val(self, mock_simple):
        """The request includes the cookie, but also an explicit value."""
        mock_simple.search.return_value = {'form': SimpleSearchForm()}, 200, {}
        ui.PARAMS_TO_PERSIST = ['foo', 'baz']
        ui.PARAMS_COOKIE_NAME = 'foo-cookie'
        self.client.set_cookie('', ui.PARAMS_COOKIE_NAME,
                               json.dumps({'foo': 'ack'}))
        response = self.client.get('/?foo=oof')
        self.assertEqual(mock_simple.search.call_args[0][0]['foo'], 'oof',
                         'The explicit value should be used')
