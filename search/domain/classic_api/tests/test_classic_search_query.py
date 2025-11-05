# File: search/domain/classic_api/tests/test_classic_input.py
# Desc: Test modifying the classic search api search_query parameter.
#       A pre-filter on user input.

from unittest import TestCase, skip
from werkzeug.exceptions import BadRequest

import search.domain.classic_api.classic_search_query as csq

ALIASES = [
    ["JUNKlastUpdatedDate:JUNK",
     "JUNKsubmittedDate:JUNK"]
]

class TestAliases(TestCase):
    def test_fix_aliases(self):
        for case in ALIASES:
            q = csq.fix_aliases(case[0])
            self.assertEqual(q, case[1])


PARTIAL_START_DATES = [
    [None, None],
    ["", ""],
    ["a", "a"],
    ["1", "1"],
    # yyyymmddhhmm
    ["199102130930",
     "199102130930"],
    ["19910213",
     "199102130000"],
    ["199102",
     "199102010000"],
    ["1991",
     "199101010000"],
]
PARTIAL_END_DATES = [
    [None, None],
    ["", ""],
    ["a", "a"],
    ["1", "1"],
    # yyyymmddhhmm
    ["202204050630",
     "202204050630"],
    ["20220405",
     "202204052359"],
    ["202001",
     "202001312359"],
    ["202002",
     "202002292359"],
    ["2022",
     "202212312359"],
    ["202010",
     "202010312359"],

    ["20",
     "20"],
    ["20201",
     "20201"],
    ["202099",
     "202099"],
]
PARTIAL_FAIL_DATES = [
    ["2022",
     "202212312350"],
]

class TestPartialSubmissionDates(TestCase):
    def test_partial_start_dates(self):
        for case in PARTIAL_START_DATES:
            q = csq.fill_in_partial_dates(case[0], True)
            self.assertEqual(q, case[1])
    def test_partial_end_dates(self):
        for case in PARTIAL_END_DATES:
            q = csq.fill_in_partial_dates(case[0], False)
            self.assertEqual(q, case[1])
    def test_partial_fail_dates(self):
        for case in PARTIAL_FAIL_DATES:
            q = csq.fill_in_partial_dates(case[0], False)
            self.assertNotEqual(q, case[1])

DATE_RANGES = [
    [None, None],
    ["", ""],
    ["a", "a"],
    ['submittedDate:[199102130930 TO 202204050630]',
     'submittedDate:"199102130930 TO 202204050630"'],
    ['submittedDate:"199102130930 TO 202204050630"',
     'submittedDate:"199102130930 TO 202204050630"'],
    ['submittedDate:[1991 TO 2022]',
     'submittedDate:"199101010000 TO 202212312359"'],
    ['a submittedDate:[1991 TO 2022] b',
     'a submittedDate:"199101010000 TO 202212312359" b'],
]

class TestSubmissionDateRanges(TestCase):
    def test_submitted_date_quotes(self):
        for case in DATE_RANGES:
            q = csq.fix_dates(case[0])
            self.assertEqual(q, case[1])


QUERIES_INTO_WORDS = [
    [None,         None],
    ['',           None],
    ['a',          ['a']],
    ['a b',        ['a', 'b']],
    ['au:',        ['au:']],
    ['au:a',       ['au:', 'a']],
    ['au:)',       ['au:', ')']],
    ['() au: a',   ['(', ')', 'au:', 'a']],
    ['ti:"a"',     ['ti:', '"a"']],
    ['title:"a"',  ['title:', '"a"']],
    ['"a',         ['a']],
    ['ti:""',      ['ti:', '""']],
    ['a OR b',     ['a', 'OR', 'b']],
    ['a AND b',    ['a', 'AND', 'b']],
    ['a ANDNOT b', ['a', 'ANDNOT', 'b']],
    ['a ORR b',    ['a', 'ORR', 'b']],
    ['ANDNOT a',   ['ANDNOT', 'a']],
    ['doi:a',      ['doi:', 'a']],
]

class TestTokenizeQuery(TestCase):
    def test_splitting_query_into_words(self):
        for case in QUERIES_INTO_WORDS:
            q = csq.split_query_into_words(case[0])
            self.assertEqual(q, case[1])


QUERIES_INTO_TOKENS = [
    [None,       None],
    ['',         None],
    ['a',        [ [csq.TEXT,'a'] ]],
    ['au:a',     [ [csq.PREFIX,'au:'], [csq.TEXT,'a']  ]],
    ['au:"a"',   [ [csq.PREFIX,'au:'], [csq.TEXT,'"a"']  ]],
    ['a OR b',   [ [csq.TEXT,'a'], [csq.OPERATOR,'OR'], [csq.TEXT,'b'] ]],
]
class TestTokenizeWords(TestCase):
    def test_making_tokens(self):
        for case in QUERIES_INTO_TOKENS:
            q = csq.tokenize(case[0])
            self.assertEqual(q, case[1])


NOT_TO_ANDNOT = [
    # ANDNOT
    [ [ [csq.OPERATOR,'ANDNOT']],
      [ [csq.OPERATOR,'ANDNOT']]],
    # NOT
    [ [ [csq.OPERATOR,'NOT']],
      [ [csq.OPERATOR,'ANDNOT']]],
    # AND+(NOT
    [ [ [csq.OPERATOR,'AND'], [csq.LEFT_PAREND,'('], [csq.OPERATOR,'NOT']],
      [ [csq.OPERATOR,'AND'], [csq.LEFT_PAREND,'('], [csq.OPERATOR,'ANDNOT']]],
    # AND+NOT
    [ [ [csq.OPERATOR,'AND'], [csq.OPERATOR,'NOT']],
      [ [csq.OPERATOR,'ANDNOT']]],
]


CONVERT_PREFIXES = [
    [ [ [csq.PREFIX, 'title:']],
      [ [csq.PREFIX, 'ti:']]],
]

PREFIXES_WITH_NO_CONTENT = [
    [ [ [csq.PREFIX, 'ti:']],
      [ ]],
    [ [ [csq.PREFIX, 'ti:'], [csq.TEXT,'a']],
      [ [csq.PREFIX, 'ti:'], [csq.TEXT,'a']]],
    [ [ [csq.OPERATOR,'NOT'], [csq.PREFIX, 'ti:'], [csq.TEXT,'a']],
      [ [csq.OPERATOR,'NOT'], [csq.PREFIX, 'ti:'], [csq.TEXT,'a']]],
    [ [ [csq.OPERATOR,'NOT'], [csq.PREFIX, 'ti:']],
      [ [csq.OPERATOR,'NOT']]],
    [ [ [csq.OPERATOR,'NOT'], [csq.PREFIX, 'ti:'], [csq.LEFT_PAREND,'(']],
      [ [csq.OPERATOR,'NOT'], [csq.LEFT_PAREND,'(']]],
]

# prefix-parends are, ie: ti:(apple)

PREFIX_PARENDS_IGNORES = [
    [ [ [csq.LEFT_PAREND,'('], [csq.TEXT,'a']],
      [ [csq.LEFT_PAREND,'('], [csq.TEXT,'a']]],
]

PREFIX_PARENDS1 = [ # simpler
    # ti:( -> (  # because the code deletes the outer prefix, then inserts for all text.
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'(']],
      [ [csq.LEFT_PAREND,'(']]],
    # ti:() -> ()
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.RIGHT_PAREND,')']]],
    # ti:(a) -> (ti:a)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']]],
    # ti:(a a) -> (ti:a ti:a)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('],
        [csq.TEXT,'a'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'],
        [csq.TEXT,'a'], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']]],
    # ti:(a)ti:(a) -> (ti:a)(ti:a)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'],
        [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'],
        [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']]],
    # ti:((a)) -> ((ti:a))
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.LEFT_PAREND,'('],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.LEFT_PAREND,'('],[csq.PREFIX,'ti:'],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'], [csq.RIGHT_PAREND,')']]],
    # ti:(a AND a) -> (ti:a AND ti:a)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.OPERATOR,'AND'],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.OPERATOR,'AND'],
        [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']]],
]

PREFIX_PARENDS2 = [ # unbalanced
    # ti:((a) -> ((ti:a)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.LEFT_PAREND,'('],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']]],
    # ti:(a)) -> (ti:a))
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'],
        [csq.TEXT,'a'], [csq.RIGHT_PAREND,')'], [csq.RIGHT_PAREND,')']]],
]

PREFIX_PARENDS3 = [ # more complicated parends
    # ti:((a AND b) c) -> ((ti:a AND ti:b) ti:c)
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('],
        [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.OPERATOR,'AND'], [csq.TEXT,'b'], [csq.RIGHT_PAREND,')'],
        [csq.TEXT,'c'], [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.OPERATOR,'AND'],
        [csq.PREFIX,'ti:'], [csq.TEXT,'b'], [csq.RIGHT_PAREND,')'],
        [csq.PREFIX,'ti:'], [csq.TEXT,'c'], [csq.RIGHT_PAREND,')']]],
    # ti:(a AND (b OR c)) -> (ti:a AND (ti:b OR ti:c))
    [ [ [csq.PREFIX,'ti:'], [csq.LEFT_PAREND,'('], [csq.TEXT,'a'], [csq.OPERATOR,'AND'],
        [csq.LEFT_PAREND,'('], [csq.TEXT,'b'], [csq.OPERATOR,'OR'], [csq.TEXT,'c'], [csq.RIGHT_PAREND,')'],
        [csq.RIGHT_PAREND,')']],
      [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'a'], [csq.OPERATOR,'AND'],
        [csq.LEFT_PAREND,'('], [csq.PREFIX,'ti:'], [csq.TEXT,'b'], [csq.OPERATOR,'OR'],
        [csq.PREFIX,'ti:'], [csq.TEXT,'c'], [csq.RIGHT_PAREND,')'], [csq.RIGHT_PAREND,')']]],
]

TOKEN_ARRAYS_MISSING_PREFIXES = [
    [ [ [csq.TEXT,'a'] ],
      [ [csq.PREFIX,'all:'],[csq.TEXT,'a'] ]],
]

TOKEN_ARRAYS_MISSING_OPERATORS = [
    [ [ [csq.TEXT,'a'], [csq.TEXT,'b'] ],
      [ [csq.TEXT,'a'], [csq.OPERATOR,'OR'], [csq.TEXT,'b'] ]],
]

TOKEN_ARRAYS_AUTHOR_UNDERSCORES = [
    [ [ [csq.PREFIX,'au:'], [csq.TEXT,'a_b'] ],
      [ [csq.PREFIX,'au:'], [csq.TEXT,'"a b"'] ]],
    [ [ [csq.PREFIX,'au:'], [csq.TEXT,'"a_b"'] ],
      [ [csq.PREFIX,'au:'], [csq.TEXT,'"a b"'] ]],
]


TOKEN_ARRAYS_MULTIPLE_OPERATORS = [
    [ [ [csq.OPERATOR,'OR'], [csq.OPERATOR,'AND'] ],
      [ [csq.OPERATOR,'AND'] ]],
    [ [ [csq.TEXT,'a'], [csq.OPERATOR,'AND'], [csq.OPERATOR,'OR'], [csq.TEXT,'b'] ],
      [ [csq.TEXT,'a'], [csq.OPERATOR,'OR'], [csq.TEXT,'b'] ]],
    [ [ [csq.TEXT,'a'], [csq.OPERATOR,'OR'], [csq.OPERATOR,'OR'], [csq.OPERATOR,'AND'], [csq.TEXT,'b'] ],
      [ [csq.TEXT,'a'], [csq.OPERATOR,'AND'], [csq.TEXT,'b'] ]],
]

TOKEN_ARRAYS_THAT_ARE_OK = [
    [None,       None],
    [[],         []],
]

# Test making changes to the search query, after it's been tokenized.
class TestReformattingTokens(TestCase):
    def test_not_into_andnot(self):
        for case in NOT_TO_ANDNOT:
            q = csq.not_into_andnot(case[0])
            self.assertEqual(q, case[1])

    def test_remove_prefixes_with_no_content(self):
        for case in PREFIXES_WITH_NO_CONTENT:
            q = csq.remove_prefixes_with_no_content(case[0])
            self.assertEqual(q, case[1])

    def test_not_into_andnot(self):
        for case in CONVERT_PREFIXES:
            q = csq.convert_prefixes(case[0])
            self.assertEqual(q, case[1])

    # prefix-parend
    def test_fix_prefix_parends_ignores(self):
        for case in PREFIX_PARENDS_IGNORES:
            q = csq.fix_prefix_parends(case[0])
            self.assertEqual(q, case[1])
    def test_fix_prefix_parends1(self):
        for case in PREFIX_PARENDS1:
            q = csq.fix_prefix_parends(case[0])
            self.assertEqual(q, case[1])
    def test_fix_prefix_parends2(self):
        for case in PREFIX_PARENDS2:
            q = csq.fix_prefix_parends(case[0])
            self.assertEqual(q, case[1])
    def test_fix_prefix_parends3(self):
        for case in PREFIX_PARENDS3:
            q = csq.fix_prefix_parends(case[0])
            self.assertEqual(q, case[1])

    def test_fix_missing_prefixes(self):
        for case in TOKEN_ARRAYS_MISSING_PREFIXES:
            q = csq.fix_missing_prefixes(case[0])
            self.assertEqual(q, case[1])

    def test_fix_missing_operators(self):
        for case in TOKEN_ARRAYS_MISSING_OPERATORS:
            q = csq.fix_missing_operators(case[0])
            self.assertEqual(q, case[1])

    def test_fix_author_underscores(self):
        for case in TOKEN_ARRAYS_AUTHOR_UNDERSCORES:
            q = csq.fix_author_underscores(case[0])
            self.assertEqual(q, case[1])

    def test_fix_multiple_operators(self):
        for case in TOKEN_ARRAYS_MULTIPLE_OPERATORS:
            q = csq.fix_multiple_operators(case[0])
            self.assertEqual(q, case[1])


    def test_token_arrays_that_are_already_valid(self):
        for case in TOKEN_ARRAYS_THAT_ARE_OK:
            q = csq.reformat(case[0])
            self.assertEqual(q, case[1])



TOKENS_INTO_QUERY = [
    [ None, None],
    [ [],   None],

    [ [ [csq.TEXT,'a'] ], 'a'],

    [ [ [csq.LEFT_PAREND,'('], [csq.PREFIX,'a']],      '(a'],
    [ [ [csq.TEXT,'a'], [csq.RIGHT_PAREND,')']],       'a)'],
    [ [ [csq.PREFIX,'a:'], [csq.TEXT,'a']],            'a:a'],
    [ [ [csq.OPERATOR,'NOT'], [csq.TEXT,'a']],         'NOT a'],
    [ [ [csq.OPERATOR,'NOT'], [csq.RIGHT_PAREND,'(']], 'NOT ('],

    [ [ [csq.TEXT,'a'], [csq.OPERATOR,'OR'], [csq.TEXT,'b']], 'a OR b'],
]
class TestTokensToQuery(TestCase):
    def test_converting_tokens_back_into_a_query(self):
        for case in TOKENS_INTO_QUERY:
            q = csq.tokens_into_query(case[0])
            self.assertEqual(q, case[1])


ADAPT_QUERIES = [
    [None, None],
    ['', None],
    ['a', 'all:a'],
    ['AND AND AND', 'AND'],
    ['a AND AND AND b', 'all:a AND all:b'],
    ['a AND au:', 'all:a AND'],
]

# Full black-box tests
class TestAdaptQuery(TestCase):
    def test_adapt_query(self):
        for case in ADAPT_QUERIES:
            q = csq.adapt_query(case[0])
            self.assertEqual(q, case[1])
