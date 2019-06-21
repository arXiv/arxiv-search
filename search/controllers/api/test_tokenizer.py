from ..api import _tokenizer as _tokenizer
from unittest import TestCase

class TestParsing(TestCase):

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