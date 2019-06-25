"""Tests for reindexing."""

from unittest import TestCase, mock

from search.services.index import classic
from ....domain import ClassicAPIQuery, Phrase, Term, Expression, Field, Operator


class TestClassicSearch(TestCase):

    def test_term_to_query_string(self):
        # test author
        result = classic._term_to_query_string((Field('au'), 'Hawking'))
        self.assertEqual(result, 'authors:Hawking')
        
        # test multi-word title
        result = classic._term_to_query_string((Field.Title, '"this that and the other"'))
        self.assertEqual(result, 'title:"this that and the other"')

    def test_phrase_to_query_string(self):
        # simplest phrase - a term
        result = classic._phrase_to_query_string((Field.Author, 'copernicus'))
        self.assertEqual(result, 'authors:copernicus')

        # simple phrase - a triple of two terms and an operator
        result = classic._phrase_to_query_string(
            ((Field.Author, 'del_maestro'),
             Operator.AND,
             (Field.Title, 'checkerboard'))
        )
        self.assertEqual(result, 'authors:del_maestro AND title:checkerboard')

        # unary NOT
        result = classic._phrase_to_query_string(
            (Operator.ANDNOT, (Field.Author, 'copernicus'))
        )
        self.assertEqual(result, 'NOT authors:copernicus')

        # nested phrases - second position
        result = classic._phrase_to_query_string(
            ((Field.Author, 'del_maestro'),
             Operator.ANDNOT,
             ((Field.Title, 'checkerboard'),
                   Operator.OR,
                   (Field.Title, 'Pyrochlore'))))
        self.assertEqual(result, "authors:del_maestro NOT (title:checkerboard OR title:Pyrochlore)")

        # nested unary not
        result = classic._phrase_to_query_string(
            ((Field.Author, 'del_maestro'),
                  Operator.OR,
                  (Operator.ANDNOT, (Field.Title, 'checkerboard')))
        )
        self.assertEqual(result, "authors:del_maestro OR (NOT title:checkerboard)")

        # nested phrases - both first and end
        result = classic._phrase_to_query_string(
            (((Field.Title, 'checkerboard'), Operator.OR, (Field.Title, 'Pyrochlore')),
             Operator.AND,
             ((Field.Author, 'del_maestro'), Operator.OR, (Field.Author, 'hawking')))
        )
        self.assertEqual(result, '(title:checkerboard OR title:Pyrochlore) AND (authors:del_maestro OR authors:hawking)')



        