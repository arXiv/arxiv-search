"""Tests exception handling in :mod:`arxiv.base.exceptions`."""

from unittest import TestCase, mock
from flask import Flask

from arxiv import status
from search.factory import create_ui_web_app
from arxiv.base.exceptions import InternalServerError
from search.services.index import IndexConnectionError, QueryError


class TestExceptionHandling(TestCase):
    """HTTPExceptions should be handled with custom templates."""

    def setUp(self):
        """Initialize an app and install :class:`.Base`."""
        self.app = create_ui_web_app()
        self.client = self.app.test_client()

    def test_404(self):
        """A 404 response should be returned."""
        response = self.client.get('/foo')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('text/html', response.content_type)

    def test_405(self):
        """A 405 response should be returned."""
        response = self.client.post('/')
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn('text/html', response.content_type)

    @mock.patch('search.controllers.simple.search')
    def test_500(self, mock_search):
        """A 500 response should be returned."""
        # Raise an internal server error from the search controller.
        mock_search.side_effect = InternalServerError

        response = self.client.get('/')
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('text/html', response.content_type)

    @mock.patch('search.controllers.simple.index')
    def test_index_connection_error(self, mock_index):
        """When an IndexConnectionError occurs, an error page is displayed."""
        mock_index.IndexConnectionError = IndexConnectionError
        mock_index.search.side_effect = IndexConnectionError
        response = self.client.get('/?searchtype=title&query=foo')
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('text/html', response.content_type)

    @mock.patch('search.controllers.simple.index')
    def test_query_error(self, mock_index):
        """When a QueryError occurs, an error page is displayed."""
        mock_index.IndexConnectionError = IndexConnectionError
        mock_index.QueryError = QueryError
        mock_index.search.side_effect = QueryError
        response = self.client.get('/?searchtype=title&query=foo')
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('text/html', response.content_type)
