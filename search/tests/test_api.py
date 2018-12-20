from unittest import TestCase, mock

from arxiv import taxonomy, status
from search.factory import create_api_web_app


class TestAdvancedSearch(TestCase):
    """Tests for the search API."""

    def setUp(self):
        """Instantiate the API application."""
        self.app = create_api_web_app()
        self.client = self.app.test_client()
