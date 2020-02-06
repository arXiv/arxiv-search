"""Tests for :mod:`search.controllers`."""

from unittest import TestCase, mock
from datetime import date

from arxiv import status
from search.domain import DocumentSet, Document
from search.controllers import health_check
from .util import catch_underscore_syntax


class TestHealthCheck(TestCase):
    """Tests for :func:`.health_check`."""

    @mock.patch("search.controllers.index.SearchSession")
    def test_index_is_down(self, mock_index):
        """Test returns 'DOWN' + status 500 when index raises an exception."""
        mock_index.search.side_effect = RuntimeError
        response, status_code, _ = health_check()
        self.assertEqual(response, "DOWN", "Response content should be DOWN")
        self.assertEqual(
            status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Should return 500 status code.",
        )

    @mock.patch("search.controllers.index.SearchSession")
    def test_index_returns_no_result(self, mock_index):
        """Test returns 'DOWN' + status 500 when index returns no results."""
        mock_index.search.return_value = dict(metadata={}, results=[])
        response, status_code, _ = health_check()
        self.assertEqual(response, "DOWN", "Response content should be DOWN")
        self.assertEqual(
            status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Should return 500 status code.",
        )

    @mock.patch("search.controllers.index.SearchSession")
    def test_index_returns_result(self, mock_index):
        """Test returns 'OK' + status 200 when index returns results."""
        mock_index.search.return_value = dict(metadata={}, results=[dict()])
        response, status_code, _ = health_check()
        self.assertEqual(response, "OK", "Response content should be OK")
        self.assertEqual(
            status_code, status.HTTP_200_OK, "Should return 200 status code."
        )


class TestUnderscoreHandling(TestCase):
    """Test :func:`.catch_underscore_syntax`."""

    def test_underscore_is_rewritten(self):
        """User searches for an author name with `surname_f` format."""
        query = "franklin_r"
        after, classic_name = catch_underscore_syntax(query)
        self.assertEqual(
            after,
            "franklin, r",
            "The underscore should be replaced with `, `.",
        )
        self.assertTrue(classic_name, "Should be identified as classic")

    def test_false_positive(self):
        """The underscore is followed by more than one character."""
        query = "not_aname"
        after, classic_name = catch_underscore_syntax(query)
        self.assertEqual(query, after, "The query should not be rewritten")
        self.assertFalse(classic_name, "Should not be identified as classic")

    def test_multiple_authors(self):
        """The user passes more than one name in classic format."""
        # E-gads.
        query = "franklin_r dole_b"
        after, classic_name = catch_underscore_syntax(query)
        self.assertEqual(
            after,
            "franklin, r; dole, b",
            "The underscore should be replaced with `, `.",
        )
        self.assertTrue(classic_name, "Should be identified as classic")

    def test_nonsense_input(self):
        """Garbage input is passed."""
        try:
            catch_underscore_syntax("")
        except Exception as ex:
            self.fail(ex)
