from unittest import TestCase
from datetime import date
from dateutil.relativedelta import relativedelta
from search.domain import Query, DateRange, FieldedSearchTerm, Classification
from search.process import query


class TestUpdatequeryWithClassification(TestCase):
    """:func:`.query._update_query_with_classification` adds classification."""

    def test_classification_is_selected(self):
        """Selected classifications are added to the query."""
        class_data = {'computer_science': True}
        q = query._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 1)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertEqual(q.primary_classification[0].archive, 'cs')
        self.assertEqual(q.primary_classification[0].group, 'cs')

    def test_multiple_classifications_are_selected(self):
        """Selected classifications are added to the query."""
        class_data = {'computer_science': True, 'eess': True}
        q = query._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 2)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsInstance(q.primary_classification[1], Classification)

    def test_physics_is_selected_all_archives(self):
        """The physics group is added to the query."""
        class_data = {'physics': True, 'physics_archives': 'all'}
        q = query._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 1)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsNone(q.primary_classification[0].archive)
        self.assertEqual(q.primary_classification[0].group, 'physics')

    def test_physics_is_selected_specific_archive(self):
        """The physic group and specified archive are added to the query."""
        class_data = {'physics': True, 'physics_archives': 'hep-ex'}
        q = query._update_query_with_classification(Query(), class_data)
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
        q = query._update_query_with_classification(Query(), class_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.primary_classification, list)
        self.assertEqual(len(q.primary_classification), 2)
        self.assertIsInstance(q.primary_classification[0], Classification)
        self.assertIsInstance(q.primary_classification[1], Classification)


class TestUpdateQueryWithFieldedTerms(TestCase):
    """:func:`.query._update_query_with_terms` applies primary search terms."""

    def test_terms_are_provided(self):
        """Selected terms are added to the query."""
        terms_data = [{'term': 'muon', 'operator': 'AND', 'field': 'title'}]
        q = query._update_query_with_terms(Query(), terms_data)
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
        q = query._update_query_with_terms(Query(), terms_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.terms, list)
        self.assertEqual(len(q.terms), 2)
        self.assertIsInstance(q.terms[0], FieldedSearchTerm)
        self.assertEqual(q.terms[1].term, 'boson')
        self.assertEqual(q.terms[1].operator, 'OR')
        self.assertEqual(q.terms[1].field, 'title')


class TestUpdateQueryWithDates(TestCase):
    """:func:`.query._update_query_with_dates` applies date selections."""

    def test_past_12_is_selected(self):
        """Query selects the past twelve months."""
        date_data = {'past_12': True}
        q = query._update_query_with_dates(Query(), date_data)
        self.assertIsInstance(q, Query)
        self.assertIsInstance(q.date_range, DateRange)
        self.assertEqual(
            q.date_range.start_date,
            date.today() - relativedelta(months=12, days=date.today().day - 1),
            "Start date is the first day of the month twelve prior to today."
        )

    def test_all_dates_is_selected(self):
        """Query does not select on date."""
        date_data = {'all_dates': True}
        q = query._update_query_with_dates(Query(), date_data)
        self.assertIsInstance(q, Query)
        self.assertIsNone(q.date_range)

    def test_specific_year_is_selected(self):
        """Start and end dates are set, one year apart."""
        date_data = {'specific_year': True, 'year': 1999}
        q = query._update_query_with_dates(Query(), date_data)
        self.assertIsInstance(q, Query)
        self.assertEqual(q.date_range.end_date,
                         date(year=2000, month=1, day=1))
        self.assertEqual(q.date_range.start_date,
                         date(year=1999, month=1, day=1))

    def test_date_range_is_selected(self):
        """Start and end dates are set based on selection."""
        from_date = date(year=1999, month=7, day=3)
        to_date = date(year=1999, month=8, day=5)
        date_data = {
            'date_range': True,
            'from_date': from_date,
            'to_date': to_date
        }
        q = query._update_query_with_dates(Query(), date_data)
        self.assertIsInstance(q, Query)
        self.assertEqual(q.date_range.end_date, to_date)
        self.assertEqual(q.date_range.start_date, from_date)
