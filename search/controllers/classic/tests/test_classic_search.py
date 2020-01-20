from unittest import TestCase, mock
from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest
from arxiv import status
from search.controllers import classic


class TestClassicAPISearch(TestCase):
    """Tests for :func:`.api.classic_query`."""

    @mock.patch(f'{classic.__name__}.index.SearchSession')
    def test_no_params(self, mock_index):
        """Request with no parameters."""
        params = MultiDict({})
        with self.assertRaises(BadRequest):
            data, code, headers = classic.query(params)

    @mock.patch(f'{classic.__name__}.index.SearchSession')
    def test_classic_query(self, mock_index):
        """Request with search_query."""
        params = MultiDict({'search_query': 'au:Copernicus'})

        data, code, headers = classic.query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f'{classic.__name__}.index.SearchSession')
    def test_classic_query_with_quotes(self, mock_index):
        """Request with search_query that includes a quoted phrase."""
        params = MultiDict({'search_query': 'ti:"dark matter"'})

        data, code, headers = classic.query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f'{classic.__name__}.index.SearchSession')
    def test_classic_id_list(self, mock_index):
        """Request with multi-element id_list with versioned and unversioned ids."""
        params = MultiDict({'id_list': '1234.56789,1234.56789v3'})

        data, code, headers = classic.query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")