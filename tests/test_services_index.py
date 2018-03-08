from unittest import TestCase, mock
from datetime import date, datetime
from pytz import timezone
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.query import Range, Match, Bool, Nested

from search.services import index
from search.domain import Query, FieldedSearchTerm, DateRange, Classification,\
    AdvancedQuery, FieldedSearchList, ClassificationList

EASTERN = timezone('US/Eastern')


class TestWildcardSearch(TestCase):
    """A wildcard [*?] character is present in a querystring."""

    def test_match_any_wildcard_is_present(self):
        """A * wildcard is present in the query."""
        qs = "Foo t*"
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertTrue(wildcard, "Wildcard should be detected")
        self.assertEqual(qs, qs_escaped, "The querystring should be unchanged")
        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('wildcard', title=qs),
            "Wildcard Q object should be generated"
        )

    def test_match_any_wildcard_in_literal(self):
        """A * wildcard is present in a string literal."""
        qs = '"Foo t*"'
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertEqual(qs_escaped, '"Foo t\*"', "Wildcard should be escaped")
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('match', title='"Foo t\*"'),
            "Wildcard Q object should not be generated"
        )

    def test_multiple_match_any_wildcard_in_literal(self):
        """Multiple * wildcards are present in a string literal."""
        qs = '"Fo*o t*"'
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertEqual(qs_escaped, '"Fo\*o t\*"',
                         "Both wildcards should be escaped")
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('match', title='"Fo\*o t\*"'),
            "Wildcard Q object should not be generated"
        )

    def test_mixed_wildcards_in_literal(self):
        """Both * and ? characters are present in a string literal."""
        qs = '"Fo? t*"'
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertEqual(qs_escaped, '"Fo\? t\*"',
                         "Both wildcards should be escaped")
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('match', title='"Fo\? t\*"'),
            "Wildcard Q object should not be generated"
        )

    def test_wildcards_both_inside_and_outside_literal(self):
        """Wildcard characters are present both inside and outside literal."""
        qs = '"Fo? t*" said the *'
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertEqual(qs_escaped, '"Fo\? t\*" said the *',
                         "Wildcards in literal should be escaped")
        self.assertTrue(wildcard, "Wildcard should be detected")
        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('wildcard', title='"Fo\? t\*" said the *'),
            "Wildcard Q object should be generated"
        )

    def test_wildcards_inside_outside_multiple_literals(self):
        """Wildcard chars are everywhere, and there are multiple literals."""
        qs = '"Fo?" s* "yes*" o?'
        qs_escaped, wildcard = index._wildcardEscape(qs)

        self.assertEqual(qs_escaped, '"Fo\?" s* "yes\*" o?',
                         "Wildcards in literal should be escaped")
        self.assertTrue(wildcard, "Wildcard should be detected")

        self.assertEqual(
            index._Q('match', 'title', qs),
            index.Q('wildcard', title='"Fo\?" s* "yes\*" o?'),
            "Wildcard Q object should be generated"
        )

    def test_wildcard_at_opening_of_string(self):
        """A wildcard character is the first character in the querystring."""
        with self.assertRaises(index.QueryError):
            index._wildcardEscape("*nope")

        with self.assertRaises(index.QueryError):
            index._Q('match', 'title', '*nope')



class TestPrepare(TestCase):
    """
    Tests for :meth:`.index.SearchSession._prepare`.

    :meth:`.index.SearchSession._prepare` renders a :class:`.AdvancedQuery`
    to an ES :class:`.Search` using elasticsearch_dsl.
    """

    def setUp(self):
        """Get a :class:`.index.SearchSession` instance."""
        self.session = index.current_session()

    def test_group_terms(self):
        """:meth:`._group_terms` groups terms using logical precedence."""
        query = AdvancedQuery(terms=FieldedSearchList([
            FieldedSearchTerm(operator=None, field='title', term='muon'),
            FieldedSearchTerm(operator='OR', field='title', term='gluon'),
            FieldedSearchTerm(operator='NOT', field='title', term='foo'),
            FieldedSearchTerm(operator='AND', field='title', term='boson'),
        ]))
        expected = (
            FieldedSearchTerm(operator=None, field='title', term='muon'),
            'OR',
            (
              (
                FieldedSearchTerm(operator='OR', field='title', term='gluon'),
                'NOT',
                FieldedSearchTerm(operator='NOT', field='title', term='foo')
              ),
              'AND',
              FieldedSearchTerm(operator='AND', field='title', term='boson')
            )
        )
        try:
            terms = self.session._group_terms(query)
        except AssertionError:
           self.fail('Should result in a single group')
        self.assertEqual(expected, terms)

    def test_group_terms_all_and(self):
        """:meth:`._group_terms` groups terms using logical precedence."""
        query = AdvancedQuery(terms=FieldedSearchList([
            FieldedSearchTerm(operator=None, field='title', term='muon'),
            FieldedSearchTerm(operator='AND', field='title', term='gluon'),
            FieldedSearchTerm(operator='AND', field='title', term='foo'),
        ]))
        expected = (
            (
              FieldedSearchTerm(operator=None, field='title', term='muon'),
              'AND',
              FieldedSearchTerm(operator='AND', field='title', term='gluon')
            ),
            'AND',
            FieldedSearchTerm(operator='AND', field='title', term='foo')
        )
        try:
            terms = self.session._group_terms(query)
        except AssertionError:
            self.fail('Should result in a single group')
        self.assertEqual(expected, terms)
