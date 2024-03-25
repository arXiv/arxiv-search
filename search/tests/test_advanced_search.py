from http import HTTPStatus
from search.services.index.exceptions import IndexConnectionError
from unittest import TestCase, mock

from arxiv import taxonomy
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
                HTTPStatus.OK,
                "Should support shortcut for archive {archive}",
            )

    def test_nonexistant_archive_shortcut(self):
        """User requests a sub-path with non-existant archive."""
        response = self.client.get("/advanced/fooarchive")
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
            "Should return a 404 error",
        )

    @mock.patch("search.controllers.advanced.SearchSession")
    def test_es_unhandled(self, mock_index):
        """Unhandled error in ES service should result in a 500"""
        def raiseEr(*args, **kwargs):
            raise ValueError(f"Raised by {__file__}")

        mock_index.current_session.side_effect = raiseEr
        response = self.client.get("""/advanced?advanced=1&terms-0-operator=AND&"""
                                   """terms-0-term=onion&terms-0-field=title""")
        self.assertEqual(
            response.status_code,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "When service raises a strange error, 500"
            )


    @mock.patch("search.controllers.advanced.SearchSession")
    def test_es_down(self, mock_index):
        """Failure to contact ES should result in a BAD_GATEWAY to distinguishsh it from
        more general 500 errors."""
        def raiseEr(*args, **kwargs):
            raise IndexConnectionError("Raised by {__file__}")

        mock_index.current_session.side_effect = raiseEr
        response = self.client.get("""/advanced?advanced=1&terms-0-operator=AND&"""
                                   """terms-0-term=onion&terms-0-field=title""")
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_GATEWAY,
            "When ES is down return BAD_GATEWAY. ARXIVNG-5112",
            )
