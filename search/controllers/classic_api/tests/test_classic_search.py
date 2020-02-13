from http import HTTPStatus
from unittest import TestCase, mock

from werkzeug import MultiDict
from werkzeug.exceptions import BadRequest

from search import domain
from search.errors import ValidationError
from search.controllers import classic_api


class TestClassicAPISearch(TestCase):
    """Tests for :func:`.classic_api.query`."""

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_no_params(self, mock_index):
        """Request with no parameters."""
        params = MultiDict({})
        with self.assertRaises(BadRequest):
            _, _, _ = classic_api.query(params)

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_query(self, mock_index):
        """Request with search_query."""
        params = MultiDict({"search_query": "au:Copernicus"})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIsNotNone(data.results, "Results are returned")
        self.assertIsNotNone(data.query, "Query object is returned")

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_query_with_quotes(self, mock_index):
        """Request with search_query that includes a quoted phrase."""
        params = MultiDict({"search_query": 'ti:"dark matter"'})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIsNotNone(data.results, "Results are returned")
        self.assertIsNotNone(data.query, "Query object is returned")

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_id_list(self, mock_index):
        """Request with multi-element id_list with (un)versioned ids."""
        params = MultiDict({"id_list": "1234.56789,1234.56789v3"})

        data, code, headers = classic_api.query(params)
        self.assertEqual(code, HTTPStatus.OK, "Returns 200 OK")
        self.assertIsNotNone(data.results, "Results are returned")
        self.assertIsNotNone(data.query, "Query object is returned")

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_start(self, mock_index):
        # Default value
        params = MultiDict({"search_query": "au:Copernicus"})
        data, _, _ = classic_api.query(params)
        self.assertEqual(data.query.page_start, 0)
        # Valid value
        params = MultiDict({"search_query": "au:Copernicus", "start": "50"})
        data, _, _ = classic_api.query(params)
        self.assertEqual(data.query.page_start, 50)
        # Invalid value
        params = MultiDict({"search_query": "au:Copernicus", "start": "-1"})
        with self.assertRaises(ValidationError):
            data, _, _ = classic_api.query(params)
        params = MultiDict({"search_query": "au:Copernicus", "start": "foo"})
        with self.assertRaises(ValidationError):
            data, _, _ = classic_api.query(params)

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_max_result(self, mock_index):
        # Default value
        params = MultiDict({"search_query": "au:Copernicus"})
        data, _, _ = classic_api.query(params)
        self.assertEqual(data.query.size, 10)
        # Valid value
        params = MultiDict(
            {"search_query": "au:Copernicus", "max_results": "50"}
        )
        data, _, _ = classic_api.query(params)
        self.assertEqual(data.query.size, 50)
        # Invalid value
        params = MultiDict(
            {"search_query": "au:Copernicus", "max_results": "-1"}
        )
        with self.assertRaises(ValidationError):
            _, _, _ = classic_api.query(params)
        params = MultiDict(
            {"search_query": "au:Copernicus", "max_results": "foo"}
        )
        with self.assertRaises(ValidationError):
            _, _, _ = classic_api.query(params)

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_sort_by(self, mock_index):
        # Default value
        params = MultiDict({"search_query": "au:Copernicus"})
        data, _, _ = classic_api.query(params)
        self.assertEqual(data.query.order.by, domain.SortBy.relevance)
        # Valid value
        for value in domain.SortBy:
            params = MultiDict(
                {"search_query": "au:Copernicus", "sortBy": f"{value}"}
            )
            data, _, _ = classic_api.query(params)
            self.assertEqual(data.query.order.by, value)

        # Invalid value
        params = MultiDict({"search_query": "au:Copernicus", "sortBy": "foo"})
        with self.assertRaises(ValidationError):
            data, _, _ = classic_api.query(params)

    @mock.patch(f"{classic_api.__name__}.index.SearchSession")
    def test_classic_sort_order(self, mock_index):
        # Default value
        params = MultiDict({"search_query": "au:Copernicus"})
        data, _, _ = classic_api.query(params)
        self.assertEqual(
            data.query.order.direction, domain.SortDirection.descending
        )
        # Valid value
        for value in domain.SortDirection:
            params = MultiDict(
                {"search_query": "au:Copernicus", "sortOrder": f"{value}"}
            )
            data, _, _ = classic_api.query(params)
            self.assertEqual(data.query.order.direction, value)

        # Invalid value
        params = MultiDict(
            {"search_query": "au:Copernicus", "sortOrder": "foo"}
        )
        with self.assertRaises(ValidationError):
            data, _, _ = classic_api.query(params)
