from ..api import _tokenizer as _tokenizer

from ...domain.api import Phrase, Expression, Term, ClassicAPIQuery, Field, \
    Operator

from unittest import TestCase

class TestParsing(TestCase):
    '''
    def test_simple(self):
        self.assertEqual(_tokenizer.tokenize("YES"), ["YES"])
    
    def test_two(self):
        self.assertEqual(_tokenizer.tokenize("YES NO"), ["YES", "NO"])

    def test_three(self):
        self.assertEqual(_tokenizer.tokenize("YES OR NO"), ["YES", "OR", "NO"])

    def test_paren_stripping(self):
        self.assertEqual(_tokenizer.tokenize("(YES OR NO)"), ["YES", "OR", "NO"])
    
    def test_parens(self):
        self.assertEqual(_tokenizer.tokenize("(YES OR NO) AND MAYBE"), [["YES", "OR", "NO"], "AND", "MAYBE"])
    '''
    def test_simple_query_without_nesting(self):
        """Simple query without grouping/nesting."""
        querystring = "au:copernicus"
        phrase: Phrase = (Field.Author, 'copernicus')
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_simple_query_with_unary_and_without_nesting(self):
        """Simple query with a unary operator without grouping/nesting."""
        querystring = "ANDNOT au:copernicus"
        phrase: Phrase = (Operator.ANDNOT, (Field.Author, 'copernicus'))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_simple_conjunct_query(self):
        """Simple conjunct query."""
        querystring = "au:del_maestro AND ti:checkerboard"
        phrase: Phrase = ((Field.Author, 'del_maestro'),
                          Operator.AND,
                          (Field.Title, 'checkerboard'))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_simple_conjunct_query_with_unary(self):
        """Disjunct query with an unary not."""
        querystring = "au:del_maestro OR (ANDNOT ti:checkerboard)"
        phrase = ((Field.Author, 'del_maestro'),
                  Operator.OR,
                  (Operator.ANDNOT, (Field.Title, 'checkerboard')))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_conjunct_with_nested_disjunct(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "au:del_maestro ANDNOT (ti:checkerboard OR ti:Pyrochlore)"
        phrase = ((Field.Author, 'del_maestro'),
                  Operator.ANDNOT,
                  ((Field.Title, 'checkerboard'),
                   Operator.OR,
                   (Field.Title, 'Pyrochlore')))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_conjunct_with_extra_nested_disjunct(self):
        """Conjunct query with nested disjunct query."""
        querystring = "((au:del_maestro OR au:bob)" \
                      " ANDNOT (ti:checkerboard OR ti:Pyrochlore))"
        phrase = (((Field.Author, 'del_maestro'),
                  Operator.OR, (Field.Author, 'bob')),
                  Operator.ANDNOT,
                  ((Field.Title, 'checkerboard'),
                   Operator.OR,
                   (Field.Title, 'Pyrochlore')))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_conjunct_with_nested_disjunct_first(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "(ti:checkerboard OR ti:Pyrochlore) ANDNOT au:del_maestro"
        phrase = (((Field.Title, 'checkerboard'),
                    Operator.OR,
                    (Field.Title, 'Pyrochlore')),
                   Operator.ANDNOT,
                   (Field.Author, 'del_maestro'))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)

    def test_conjunct_with_nested_phrases(self):
        """Conjunct query with nested disjunct query."""
        querystring \
            = "(ti:checkerboard OR ti:Pyrochlore) AND (au:del_maestro OR au:hawking)"
        phrase = (((Field.Title, 'checkerboard'), Operator.OR, (Field.Title, 'Pyrochlore')),
                   Operator.AND,
                   ((Field.Author, 'del_maestro'), Operator.OR, (Field.Author, 'hawking')))
        self.assertEqual(_tokenizer.tokenize(querystring), phrase)
