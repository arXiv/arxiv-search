"""Tests for classic API search."""
from http import HTTPStatus
from unittest import TestCase, mock
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest

from search.controllers import classic_api


class TestClassicAPISearch(TestCase):
    """Tests for :func:`.classic_api.query`."""

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_no_params(self, mock_index):
        """Request with no parameters."""
        params = MultiDict({})
        with self.assertRaises(BadRequest):
            data, code, headers = classic_api.query(params)

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_query(self, mock_index):
        """Request with search_query."""
        params = MultiDict({"search_query": "au:Copernicus"})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_query_with_quotes(self, mock_index):
        """Request with search_query that includes a quoted phrase."""
        params = MultiDict({"search_query": 'ti:"dark matter"'})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_id_list(self, mock_index):
        """Request with multi-element id_list with (un)versioned ids."""
        params = MultiDict({"id_list": "1234.56789,1234.56789v3"})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")
