from http import HTTPStatus
from unittest import TestCase

from arxiv import taxonomy
from search.factory import create_ui_web_app


class TestSearchs(TestCase):
    """Test for the advanced search UI."""

    def setUp(self):
        """Instantiate the UI application."""
        self.app = create_ui_web_app()
        self.client = self.app.test_client()

    #@mock.patch("search.controllers.simple.SearchSession")
    def test_bad_query(self):
        """Bad query should result in a 400 not a 500. query from ARXIVNG-2437"""
        response = self.client.get("/?query=%2F%3F&searchtype=all&source=header")
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
            "A query that cannot be parsed by ES should result in 400. ARXIVNG-2437",
            )

        response = self.client.get("/?query=+O%5E*%282.619%5Ek%29+algorithm+for+4-path+vertex+cover&searchtype=all&source=header")
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
            "A query that cannot be parsed by ES should result in 400. ARXIVNG-3971"
            )
