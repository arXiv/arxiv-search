from unittest import TestCase, mock

from elasticsearch_dsl import Search, Q

from search.services import index
from search.domain import Query, FieldedSearchTerm


class TestQueryToSearch(TestCase):
    """
    :meth:`.index.SearchSession._to_es_dsql` renders a :class:`.Query` to an
    ES :class:`.Search` using elasticsearch_dsl
    """

    def setUp(self):
        self.session = index.current_session()

    def test_to_es_dsl_returns_a_search(self):
        """Return a :class:`.Search`."""
        self.assertIsInstance(self.session._to_es_dsl(Query()), Search)

    def test_group_terms(self):
        """:meth:`._group_terms` groups terms using logical precedence."""
        query = Query({'terms': [
            FieldedSearchTerm(operator=None, field='title', term='muon'),
            FieldedSearchTerm(operator='OR', field='title', term='gluon'),
            FieldedSearchTerm(operator='NOT', field='title', term='foo'),
            FieldedSearchTerm(operator='AND', field='title', term='boson'),
        ]})
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

    def test_grouped_terms_to_q(self):
        """:meth:`._grouped_terms_to_q` an :class:`.Q` from grouped terms."""
        query = Query({'terms': [
            FieldedSearchTerm(operator=None, field='title', term='muon'),
            FieldedSearchTerm(operator='OR', field='title', term='gluon'),
            FieldedSearchTerm(operator='NOT', field='title', term='foo'),
            FieldedSearchTerm(operator='AND', field='title', term='boson'),
        ]})
        expected = (Q('match', title='muon')
                    | (
                      (Q('match', title='gluon')
                       & ~Q('match', title='foo'))
                      & Q('match', title='boson'))
                    )
        q = self.session._grouped_terms_to_q(self.session._group_terms(query))
        self.assertEqual(expected, q)

    # def test_to_es_dl_with_fieldedsearchterms(self):
    #     query = Query(terms=[
    #         FieldedSearchTerm(operator=None, field='title', term='muon'),
    #         FieldedSearchTerm(operator='OR', field='title', term='gluon'),
    #         FieldedSearchTerm(operator='NOT', field='title', term='foo'),
    #         FieldedSearchTerm(operator='AND', field='title', term='boson'),
    #     ])
    #     search = self.session._to_es_dsl(query)
        
