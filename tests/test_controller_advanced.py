"""Tests for advanced search controller, :mod:`search.controllers.advanced`."""

from unittest import TestCase, mock
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from werkzeug import MultiDict
from werkzeug.exceptions import InternalServerError

from arxiv import status

from search.domain import Query, DateRange, FieldedSearchTerm, Classification,\
    AdvancedQuery
from search.controllers import advanced
from search.controllers.advanced.forms import AdvancedSearchForm

from search.services.index import IndexConnectionError, QueryError


class TestSearchController(TestCase):
    """Tests for :func:`.advanced.search`."""

    @mock.patch('search.controllers.advanced.index')
    def test_no_form_data(self, mock_index):
        """No form data has been submitted."""
        request_data = MultiDict()
        response_data, code, headers = advanced.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.advanced.index')
    def test_single_field_term(self, mock_index):
        """Form data and ``advanced`` param are present."""
        request_data = MultiDict({
            'advanced': True,
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo'
        })
        response_data, code, headers = advanced.search(request_data)
        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], AdvancedQuery,
                              "An AdvancedQuery is passed to the search index")
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

    @mock.patch('search.controllers.advanced.index')
    def test_invalid_data(self, mock_index):
        """Form data are invalid."""
        request_data = MultiDict({
            'advanced': True,
            'date-past_12': True,
            'date-specific_year': True,
            'date-year': '2012'
        })
        response_data, code, headers = advanced.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.advanced.index')
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
            'advanced': True,
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo'
        })
        with self.assertRaises(InternalServerError):
            response_data, code, headers = advanced.search(request_data)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], AdvancedQuery,
                              "An AdvancedQuery is passed to the search index")

    @mock.patch('search.controllers.advanced.index')
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
            'advanced': True,
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo'
        })
        with self.assertRaises(InternalServerError):
            try:
                response_data, code, headers = advanced.search(request_data)
            except QueryError as e:
                self.fail("QueryError should be handled (caught %s)" % e)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")


class TestAdvancedSearchForm(TestCase):
    """Tests for :class:`.AdvancedSearchForm`."""

    def test_single_field_term(self):
        """User has entered a single term for a field-based search."""
        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo'
        })
        form = AdvancedSearchForm(data)
        self.assertTrue(form.validate())

    def test_term_starts_with_wildcard(self):
        """User has entered a string that starts with a wildcard."""
        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': '*foo'
        })
        form = AdvancedSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

    def test_specific_year_must_be_specified(self):
        """If the user selects specific year, they must indicate a year."""
        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'specific_year',
        })
        form = AdvancedSearchForm(data)
        self.assertFalse(form.validate())
        self.assertEqual(len(form.errors), 1)

        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'specific_year',
            'date-year': '2012'
        })
        form = AdvancedSearchForm(data)
        self.assertTrue(form.validate())

    def test_date_range_must_be_specified(self):
        """If the user selects date range, they must indicate start or end."""
        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'date_range',
        })
        form = AdvancedSearchForm(data)
        self.assertFalse(form.validate())
        self.assertEqual(len(form.errors), 1)

        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'date_range',
            'date-from_date': '2012-02-05'
        })
        form = AdvancedSearchForm(data)
        self.assertTrue(form.validate())

        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'date_range',
            'date-to_date': '2012-02-05'
        })
        form = AdvancedSearchForm(data)
        self.assertTrue(form.validate())

    def test_year_must_be_after_1990(self):
        """If the user selects a specific year, it must be after 1990."""
        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'specific_year',
            'date-year': '1990'
        })
        form = AdvancedSearchForm(data)
        self.assertFalse(form.validate())

        data = MultiDict({
            'terms-0-operator': 'AND',
            'terms-0-field': 'title',
            'terms-0-term': 'foo',
            'date-filter_by': 'specific_year',
            'date-year': '1991'
        })
        form = AdvancedSearchForm(data)
        self.assertTrue(form.validate())


class TestUpdatequeryWithClassification(TestCase):
    """:func:`.advanced._update_query_with_classification` adds classfnxn."""

    def test_classification_is_selected(self):
        """Selected classifications are added to the query."""
        class_data = {'computer_science': True}
        q = advanced._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 1)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertEqual(q.primary_classification[0].archive, 'cs')
        self.assertEqual(q.primary_classification[0].group, 'cs')

    def test_multiple_classifications_are_selected(self):
        """Selected classifications are added to the query."""
        class_data = {'computer_science': True, 'eess': True}
        q = advanced._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 2)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsInstance(q.primary_classification[1], Classification)

    def test_physics_is_selected_all_archives(self):
        """The physics group is added to the query."""
        class_data = {'physics': True, 'physics_archives': 'all'}
        q = advanced._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 1)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsNone(q.primary_classification[0].archive)
        self.assertEqual(q.primary_classification[0].group, 'physics')

    def test_physics_is_selected_specific_archive(self):
        """The physic group and specified archive are added to the query."""
        class_data = {'physics': True, 'physics_archives': 'hep-ex'}
        q = advanced._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 1)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertEqual(q.primary_classification[0].archive, 'hep-ex')
        self.assertEqual(q.primary_classification[0].group, 'physics')

    def test_physics_is_selected_specific_archive_plus_other_groups(self):
        """The physics group and specified archive are added to the query."""
        class_data = {
            'mathematics': True,
            'physics': True,
            'physics_archives': 'hep-ex'
        }
        q = advanced._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 2)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsInstance(q.primary_classification[1], Classification)


class TestUpdateQueryWithFieldedTerms(TestCase):
    """:func:`.advanced._update_query_with_terms` adds primary search terms."""

    def test_terms_are_provided(self):
        """Selected terms are added to the query."""
        terms_data = [{'term': 'muon', 'operator': 'AND', 'field': 'title'}]
        q = advanced._update_query_with_terms(Query(), terms_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.terms, list)
        self.assertEqual(len(q.terms), 1)
        self.assertIsInstance(q.terms[0], FieldedSearchTerm)
        self.assertEqual(q.terms[0].term, 'muon')
        self.assertEqual(q.terms[0].operator, 'AND')
        self.assertEqual(q.terms[0].field, 'title')

    def test_multiple_terms_are_provided(self):
        """Selected terms are added to the query."""
        terms_data = [
            {'term': 'muon', 'operator': 'AND', 'field': 'title'},
            {'term': 'boson', 'operator': 'OR', 'field': 'title'}
        ]
        q = advanced._update_query_with_terms(Query(), terms_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.terms, list)
        self.assertEqual(len(q.terms), 2)
        self.assertIsInstance(q.terms[0], FieldedSearchTerm)
        self.assertEqual(q.terms[1].term, 'boson')
        self.assertEqual(q.terms[1].operator, 'OR')
        self.assertEqual(q.terms[1].field, 'title')


class TestUpdateQueryWithDates(TestCase):
    """:func:`.advanced._update_query_with_dates` applies date selections."""

    def test_past_12_is_selected(self):
        """Query selects the past twelve months."""
        date_data = {'filter_by': 'past_12'}
        q = advanced._update_query_with_dates(Query(), date_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.date_range, DateRange)
        twelve_months = relativedelta(months=12, days=date.today().day - 1)
        self.assertEqual(
            q.date_range.start_date.date(),
            date.today() - twelve_months,
            "Start date is the first day of the month twelve prior to today."
        )

    def test_all_dates_is_selected(self):
        """Query does not select on date."""
        date_data = {'filter_by': 'all_dates'}
        q = advanced._update_query_with_dates(AdvancedQuery(), date_data)
        self.assertIsInstance(q, AdvancedQuery)
        self.assertIsNone(q.date_range)

    def test_specific_year_is_selected(self):
        """Start and end dates are set, one year apart."""
        date_data = {
            'filter_by': 'specific_year',
            'year': date(year=1999, month=1, day=1)
        }
        q = advanced._update_query_with_dates(AdvancedQuery(), date_data)
        self.assertIsInstance(q, AdvancedQuery)
        self.assertEqual(q.date_range.end_date.date(),
                         date(year=2000, month=1, day=1))
        self.assertEqual(q.date_range.start_date.date(),
                         date(year=1999, month=1, day=1))

    def test_date_range_is_selected(self):
        """Start and end dates are set based on selection."""
        from_date = date(year=1999, month=7, day=3)
        to_date = date(year=1999, month=8, day=5)
        date_data = {
            'filter_by': 'date_range',
            'from_date': from_date,
            'to_date': to_date,
        }
        q = advanced._update_query_with_dates(AdvancedQuery(), date_data)
        self.assertIsInstance(q, AdvancedQuery)
        self.assertEqual(q.date_range.end_date.date(), to_date)
        self.assertEqual(q.date_range.start_date.date(), from_date)
