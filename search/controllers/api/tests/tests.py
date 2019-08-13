"""Tests for advanced search controller, :mod:`search.controllers.advanced`."""

from unittest import TestCase, mock
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from werkzeug import MultiDict
from werkzeug.exceptions import InternalServerError, BadRequest

from arxiv import status

from search.domain import Query, DateRange, FieldedSearchTerm, Classification,\
    AdvancedQuery, DocumentSet
from search.controllers import api
from search.domain import api as api_domain
from search.services.index import IndexConnectionError, QueryError


class TestAPISearch(TestCase):
    """Tests for :func:`.api.search`."""

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_no_params(self, mock_index):
        """Request with no parameters."""
        params = MultiDict({})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")
        expected_fields = api_domain.get_required_fields() \
            + api_domain.get_default_extra_fields()
        self.assertEqual(set(data["query"].include_fields),
                         set(expected_fields),
                         "Default set of fields is included")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_query_param(self, mock_index):
        """Request with a query string. Tests conjuncts and quoted phrases."""
        params = MultiDict({'query' : 'au:copernicus AND ti:"dark matter"'})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")
        expected_fields = api_domain.get_required_fields() \
            + api_domain.get_default_extra_fields()
        self.assertEqual(set(data["query"].include_fields),
                         set(expected_fields),
                         "Default set of fields is included")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_include_fields(self, mock_index):
        """Request with specific fields included."""
        extra_fields = ['title', 'abstract', 'authors']
        params = MultiDict({'include': extra_fields})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")
        expected_fields = api_domain.get_required_fields() + extra_fields
        self.assertEqual(set(data["query"].include_fields),
                         set(expected_fields),
                         "Requested fields are included")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_group_primary_classification(self, mock_index):
        """Request with a group as primary classification."""
        group = 'grp_physics'
        params = MultiDict({'primary_classification': group})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertEqual(len(query.primary_classification), 1)
        self.assertEqual(query.primary_classification[0],
                         Classification(group={'id': group}))

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_archive_primary_classification(self, mock_index):
        """Request with an archive as primary classification."""
        archive = 'physics'
        params = MultiDict({'primary_classification': archive})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertEqual(len(query.primary_classification), 1)
        self.assertEqual(query.primary_classification[0],
                         Classification(archive={'id': archive}))

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_archive_subsumed_classification(self, mock_index):
        """Request with a subsumed archive as primary classification."""
        archive = 'chao-dyn'
        params = MultiDict({'primary_classification': archive})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertEqual(len(query.primary_classification), 2)
        self.assertEqual(query.primary_classification[0],
                         Classification(archive={'id': archive}))
        self.assertEqual(query.primary_classification[1],
                         Classification(archive={'id': 'nlin.CD'}),
                         "The canonical archive is used instead")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_category_primary_classification(self, mock_index):
        """Request with a category as primary classification."""
        category = 'cs.DL'
        params = MultiDict({'primary_classification': category})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertEqual(len(query.primary_classification), 1)
        self.assertEqual(query.primary_classification[0],
                         Classification(category={'id': category}))

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_bad_classification(self, mock_index):
        """Request with nonsense as primary classification."""
        params = MultiDict({'primary_classification': 'nonsense'})
        with self.assertRaises(BadRequest):
            api.search(params)

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_with_start_date(self, mock_index):
        """Request with dates specified."""
        params = MultiDict({'start_date': '1999-01-02'})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertIsNotNone(query.date_range)
        self.assertEqual(query.date_range.start_date.year, 1999)
        self.assertEqual(query.date_range.start_date.month, 1)
        self.assertEqual(query.date_range.start_date.day, 2)
        self.assertEqual(query.date_range.date_type,
                         DateRange.SUBMITTED_CURRENT,
                         "Submitted date of current version is the default")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_with_end_dates_and_type(self, mock_index):
        """Request with end date and date type specified."""
        params = MultiDict({'end_date': '1999-01-02',
                            'date_type': 'announced_date_first'})
        data, code, headers = api.search(params)

        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        query = mock_index.search.call_args[0][0]
        self.assertIsNotNone(query.date_range)
        self.assertEqual(query.date_range.end_date.year, 1999)
        self.assertEqual(query.date_range.end_date.month, 1)
        self.assertEqual(query.date_range.end_date.day, 2)

        self.assertEqual(query.date_range.date_type,
                         DateRange.ANNOUNCED)


class TestClassicAPISearch(TestCase):
    """Tests for :func:`.api.classic_query`."""

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_no_params(self, mock_index):
        """Request with no parameters."""
        params = MultiDict({})
        with self.assertRaises(BadRequest):
            data, code, headers = api.classic_query(params)

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_classic_search_query(self, mock_index):
        """Request with search_query."""
        params = MultiDict({'search_query' : 'au:Copernicus'})

        data, code, headers = api.classic_query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_classic_search_query_with_quotes(self, mock_index):
        """Request with search_query that includes a quoted phrase."""
        params = MultiDict({'search_query' : 'ti:"dark matter"'})

        data, code, headers = api.classic_query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_classic_id_list(self, mock_index):
        """Request with multi-element id_list with versioned and unversioned ids."""
        params = MultiDict({'id_list' : '1234.56789,1234.56789v3'})

        data, code, headers = api.classic_query(params)
        self.assertEqual(code, status.HTTP_200_OK, "Returns 200 OK")
        self.assertIn("results", data, "Results are returned")
        self.assertIn("query", data, "Query object is returned")

class TestPaper(TestCase):
    """Tests for :func:`.api.paper`."""
    
    @mock.patch(f'{api.__name__}.index.SearchSession')
    def test_paper(self, mock_index):
        """Request with single parameter paper."""
        params = MultiDict({})
        data, code, headers = api.paper('1234.56789')

