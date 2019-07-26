from ...api.classic_parser import parse_classic_query, serialize_query_string

from ....domain.api import Phrase, Term, ClassicAPIQuery, Field, Operator

from werkzeug.exceptions import BadRequest
from unittest import TestCase


class TestParsing(TestCase):
    def test_simple_query_without_nesting(self):
        """Simple query without grouping/nesting."""
        querystring = "au:copernicus"
        phrase: Phrase = (Field.Author, 'copernicus')
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_simple_query_with_quotes(self):
        """Simple query with quotations."""
        querystring = 'ti:"dark matter"'
        phrase: Phrase = (Field.Title, 'dark matter')
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_simple_query_with_unary_and_without_nesting(self):
        """Simple query with a unary operator without grouping/nesting."""
        querystring = "ANDNOT au:copernicus"
        phrase: Phrase = (Operator.ANDNOT, (Field.Author, 'copernicus'))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_simple_conjunct_query(self):
        """Simple conjunct query."""
        querystring = "au:del_maestro AND ti:checkerboard"
        phrase: Phrase = ((Field.Author, 'del_maestro'),
                          (Operator.AND,
                           (Field.Title, 'checkerboard')))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_simple_conjunct_query_with_quotes(self):
        """Simple conjunct query with quoted field."""
        querystring = 'au:del_maestro AND ti:"dark matter"'
        phrase: Phrase = ((Field.Author, 'del_maestro'),
                          (Operator.AND,
                           (Field.Title, 'dark matter')))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_simple_conjunct_query_with_unary(self):
        """Disjunct query with an unary not."""
        querystring = "au:del_maestro OR (ANDNOT ti:checkerboard)"
        phrase = ((Field.Author, 'del_maestro'),
                  (Operator.OR,
                   (Operator.ANDNOT, (Field.Title, 'checkerboard'))))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_conjunct_with_nested_disjunct(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "au:del_maestro ANDNOT (ti:checkerboard OR ti:Pyrochlore)"
        phrase = ((Field.Author, 'del_maestro'),
                  (Operator.ANDNOT,
                   ((Field.Title, 'checkerboard'),
                    (Operator.OR,
                     (Field.Title, 'Pyrochlore')))))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_conjunct_with_extra_nested_disjunct(self):
        """Conjunct query with nested disjunct query."""
        querystring = "((au:del_maestro OR au:bob)" \
                      " ANDNOT (ti:checkerboard OR ti:Pyrochlore))"
        phrase = (((Field.Author, 'del_maestro'),
                  (Operator.OR, (Field.Author, 'bob'))),
                  (Operator.ANDNOT,
                   ((Field.Title, 'checkerboard'),
                    (Operator.OR,
                     (Field.Title, 'Pyrochlore')))))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_conjunct_with_nested_disjunct_first(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "(ti:checkerboard OR ti:Pyrochlore) ANDNOT au:del_maestro"
        phrase = (((Field.Title, 'checkerboard'),
                    (Operator.OR,
                     (Field.Title, 'Pyrochlore'))),
                   (Operator.ANDNOT,
                    (Field.Author, 'del_maestro')))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_conjunct_with_nested_phrases(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "(ti:checkerboard OR ti:Pyrochlore) AND (au:del_maestro OR au:hawking)"
        phrase = (((Field.Title, 'checkerboard'), 
                    (Operator.OR, (Field.Title, 'Pyrochlore'))),
                  (Operator.AND,
                   ((Field.Author, 'del_maestro'), 
                    (Operator.OR, (Field.Author, 'hawking')))))
        self.assertEqual(parse_classic_query(querystring), phrase)

    def test_error_double_conjunct(self):
        querystring = "ti:a or and ti:b"
        with self.assertRaises(BadRequest):
            parse_classic_query(querystring)

    def test_error_double_operand(self):
        querystring = "ti:a and ti:b ti:c"
        with self.assertRaises(BadRequest):
            parse_classic_query(querystring)

    def test_error_trailing_operator(self):
        querystring = "ti:a and ti:b and"
        with self.assertRaises(BadRequest):
            parse_classic_query(querystring)
    
    def test_error_leading_operand(self):
        querystring = "or ti:a and ti:b"
        with self.assertRaises(BadRequest):
            parse_classic_query(querystring)
    
    def test_serialize_query(self):
        querystring = "au:copernicus"
        phrase: Phrase = (Field.Author, 'copernicus')
        self.assertEqual(serialize_query_string(phrase), querystring)

    def test_serialize_simple_query_with_quotes(self):
        """Simple query with quotations."""
        querystring = 'ti:"dark matter"'
        phrase: Phrase = (Field.Title, 'dark matter')
        self.assertEqual(serialize_query_string(phrase), querystring)

    def test_serialize_simple_conjunct_query(self):
        """Simple conjunct query."""
        querystring = "au:del_maestro AND ti:checkerboard"
        phrase: Phrase = ((Field.Author, 'del_maestro'),
                          (Operator.AND,
                           (Field.Title, 'checkerboard')))
        self.assertEqual(serialize_query_string(phrase), querystring)

    def test_serialize_conjunct_with_nested_phrases(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "(ti:checkerboard OR ti:Pyrochlore) AND (au:del_maestro OR au:hawking)"
        phrase = (((Field.Title, 'checkerboard'), 
                    (Operator.OR, (Field.Title, 'Pyrochlore'))),
                  (Operator.AND,
                   ((Field.Author, 'del_maestro'), 
                    (Operator.OR, (Field.Author, 'hawking')))))
        self.assertEqual(serialize_query_string(phrase), querystring)