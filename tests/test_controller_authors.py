"""Tests for authors search controller, :mod:`search.controllers.authors`."""

from unittest import TestCase, mock
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from werkzeug import MultiDict
from werkzeug.exceptions import InternalServerError

from arxiv import status

from search.domain import Query, DateRange, AuthorQuery

from search.controllers import authors
from search.controllers.authors.forms import AuthorSearchForm

from search.services.index import IndexConnectionError, QueryError


class TestSearchController(TestCase):
    """Tests for :func:`.authors.search`."""

    @mock.patch('search.controllers.authors.index')
    def test_no_form_data(self, mock_index):
        """No form data has been submitted."""
        request_data = MultiDict()
        response_data, code, headers = authors.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.authors.index')
    def test_single_field_term(self, mock_index):
        """Form data and ``authors`` param are present."""
        request_data = MultiDict({
            'authors-0-surname': 'davis'
        })
        response_data, code, headers = authors.search(request_data)
        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], AuthorQuery,
                              "An AuthorQuery is passed to the search index")
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

    @mock.patch('search.controllers.authors.index')
    def test_invalid_data(self, mock_index):
        """Form data are invalid."""
        request_data = MultiDict({
            'authors-0-forename': 'davis'
        })
        response_data, code, headers = authors.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.authors.index')
    def test_index_raises_connection_exception(self, mock_index):
        """Index service raises a IndexConnectionError."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.IndexConnectionError = IndexConnectionError

        def _raiseIndexConnectionError(*args, **kwargs):
            raise IndexConnectionError('What now')

        mock_index.search.side_effect = _raiseIndexConnectionError

        request_data = MultiDict({
            'authors-0-surname': 'davis'
        })
        with self.assertRaises(InternalServerError):
            response_data, code, headers = authors.search(request_data)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], AuthorQuery,
                              "An AuthorQuery is passed to the search index")


    @mock.patch('search.controllers.authors.index')
    def test_index_raises_query_error(self, mock_index):
        """Index service raises a QueryError."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.QueryError = QueryError
        mock_index.IndexConnectionError = IndexConnectionError

        def _raiseQueryError(*args, **kwargs):
            raise QueryError('What now')

        mock_index.search.side_effect = _raiseQueryError

        request_data = MultiDict({
            'authors-0-surname': 'davis'
        })
        with self.assertRaises(InternalServerError):
            try:
                response_data, code, headers = authors.search(request_data)
            except QueryError as e:
                self.fail("QueryError should be handled (caught %s)" % e)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")


class TestAuthorSearchForm(TestCase):
    """Tests for :class:`.AuthorSearchForm`."""

    def test_single_surname(self):
        """User has entered a single surname."""
        data = MultiDict({
            'authors-0-surname': 'davis'
        })
        form = AuthorSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")

    def test_single_forename(self):
        """User has entered a single forename."""
        data = MultiDict({
            'authors-0-forename': 'davis'
        })
        form = AuthorSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

    def test_single_surname_and_forename(self):
        """User has entered a single surname and forename."""
        data = MultiDict({
            'authors-0-forename': 'david',
            'authors-0-surname': 'davis'
        })
        form = AuthorSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")

    def test_multiple_surname_and_maybe_forename(self):
        """User has entered a single surname and forename."""
        data = MultiDict({
            'authors-0-forename': 'david',
            'authors-0-surname': 'davis',
            'authors-1-surname': 'franklin',
            'authors-2-forename': 'jane',
            'authors-2-surname': 'doe'
        })
        form = AuthorSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")

    def test_value_starts_with_wildcard(self):
        """User has entered a value that starts with wildcard."""
        data = MultiDict({
            'authors-0-forename': '*david',
            'authors-0-surname': 'davis'
        })
        form = AuthorSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")


class TestRewriteSimpleParams(TestCase):
    """Tests for :func:`.authors._rewrite_simple_params`."""

    def test_params_has_forename(self):
        """GET parameters include ``forename``."""
        get_params = MultiDict({'forename': 'jane'})
        params = authors._rewrite_simple_params(get_params)
        self.assertIn('authors-0-forename', params,
                      "Should rewrite as form-compatible parameter")
        self.assertEqual(params['forename'], params['authors-0-forename'])

    def test_params_has_surname(self):
        """GET parameters include ``surname``."""
        get_params = MultiDict({'surname': 'doe'})
        params = authors._rewrite_simple_params(get_params)
        self.assertIn('authors-0-surname', params,
                      "Should rewrite as form-compatible parameter")
        self.assertEqual(params['surname'], params['authors-0-surname'])


class TestQueryFromForm(TestCase):
    """Tests for :func:`.authors._query_from_form`."""

    def test_multiple_authors(self):
        """Form data has three authors."""
        data = MultiDict({
            'authors-0-forename': 'david',
            'authors-0-surname': 'davis',
            'authors-1-surname': 'franklin',
            'authors-2-forename': 'jane',
            'authors-2-surname': 'doe'
        })
        form = AuthorSearchForm(data)
        query = authors._query_from_form(form)
        self.assertIsInstance(query, AuthorQuery,
                              "Should return an instance of AuthorQuery")
        self.assertEqual(len(query.authors), 3, "Should have three authors")

    def test_form_data_has_order(self):
        """Form data includes sort order."""
        data = MultiDict({
            'authors-0-forename': 'david',
            'authors-0-surname': 'davis',
            'order': 'submitted_date'
        })
        form = AuthorSearchForm(data)
        query = authors._query_from_form(form)
        self.assertIsInstance(query, AuthorQuery,
                              "Should return an instance of AuthorQuery")
        self.assertEqual(query.order, 'submitted_date')

    def test_form_data_has_no_order(self):
        """Form data includes sort order parameter, but it is 'None'."""
        data = MultiDict({
            'authors-0-forename': 'david',
            'authors-0-surname': 'davis',
            'order': 'None'    #
        })
        form = AuthorSearchForm(data)
        query = authors._query_from_form(form)
        self.assertIsInstance(query, AuthorQuery,
                              "Should return an instance of AuthorQuery")
        self.assertIsNone(query.order, "Order should be None")
