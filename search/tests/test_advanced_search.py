from unittest import TestCase, mock

from arxiv import taxonomy, status
from search.factory import create_ui_web_app


class TestAdvancedSearch(TestCase):
    """Test for the advanced search UI."""

    def setUp(self):
        """Instantiate the UI application."""
        self.app = create_ui_web_app()
        self.client = self.app.test_client()

    def test_archive_shortcut(self):
        """User requests a sub-path with classification archive."""
        for archive in taxonomy.ARCHIVES.keys():
            response = self.client.get(f"/advanced/{archive}")
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                "Should support shortcut for archive {archive}",
            )

    def test_nonexistant_archive_shortcut(self):
        """User requests a sub-path with non-existant archive."""
        response = self.client.get("/advanced/fooarchive")
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            "Should return a 404 error",
        )
