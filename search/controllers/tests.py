from unittest import TestCase, mock

from arxiv import status
from search.domain import DocumentSet, Document
from search.controllers import health_check


class TestHealthCheck(TestCase):
    """Tests for :func:`.health_check`."""

    @mock.patch('search.controllers.index')
    def test_index_is_down(self, mock_index):
        """Test returns 'DOWN' + status 500 when index raises an exception."""
        mock_index.search.side_effect = RuntimeError
        response, status_code, _ = health_check()
        self.assertEqual(response, 'DOWN', "Response content should be DOWN")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR,
                         "Should return 500 status code.")

    @mock.patch('search.controllers.index')
    def test_index_returns_no_result(self, mock_index):
        """Test returns 'DOWN' + status 500 when index returns no results."""
        mock_index.search.return_value = DocumentSet({}, [])
        response, status_code, _ = health_check()
        self.assertEqual(response, 'DOWN', "Response content should be DOWN")
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR,
                         "Should return 500 status code.")

    @mock.patch('search.controllers.index')
    def test_index_returns_result(self, mock_index):
        """Test returns 'OK' + status 200 when index returns results."""
        mock_index.search.return_value = DocumentSet({}, [Document()])
        response, status_code, _ = health_check()
        self.assertEqual(response, 'OK', "Response content should be OK")
        self.assertEqual(status_code, status.HTTP_200_OK,
                         "Should return 200 status code.")
