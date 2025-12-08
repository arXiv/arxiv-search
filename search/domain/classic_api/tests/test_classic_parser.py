# type: ignore
"""Test cases for the classic parser."""
from typing import List
from dataclasses import dataclass

from search.domain import Phrase, Field, Operator, Term
from search.domain.classic_api.query_parser import (
    parse_classic_query,
    phrase_to_query_string,
)

from werkzeug.exceptions import BadRequest
from unittest import TestCase


@dataclass
class Case:
    message: str
    query: str
    phrase: Phrase = None


TEST_PARSE_OK_CASES: List[Case] = [
    Case(message="Empty query.", query="", phrase=Term(Field.All, ""),),
    Case(
        message="Empty query full of spaces.",
        query='au:"     "',
        phrase=Term(Field.Author, ""),
    ),
    Case(
        message="Search all fields.",
        query='all:abc',
        phrase=Term(Field.All, 'abc'),
    ),
    Case(
        message="Empty query in conjunct.",
        query='all:electron AND au:""',
        phrase=(
            Operator.AND,
            Term(Field.All, "electron"),
            Term(Field.Author, ""),
        ),
    ),
    Case(
        message="Simple query without grouping/nesting.",
        query="au:copernicus",
        phrase=Term(Field.Author, "copernicus"),
    ),
    Case(
        message="Simple abstract query.",
        query='abs:copernicus',
        phrase=Term(Field.Abstract, "copernicus"),
    ),
    Case(
        message="Simple query with quotations.",
        query='ti:"dark matter"',
        phrase=Term(Field.Title, '"dark matter"'),
    ),
    Case(
        message="Simple query with quotations and extra spacing.",
        query='ti:"  dark matter    "',
        phrase=Term(Field.Title, '"dark matter"'),
    ),
    Case(
        message="Search date ranges.",
        query='submittedDate:"202301010600 TO 202401010600"',
        phrase=Term(Field.SubmittedDate, '"202301010600 TO 202401010600"'),
    ),
    Case(
        message="Simple conjunct query.",
        query="au:del_maestro AND ti:checkerboard",
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "checkerboard"),
        ),
    ),
    Case(
        message="Simple conjunct query with quoted field.",
        query='au:del_maestro AND ti:"dark matter"',
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, '"dark matter"'),
        ),
    ),
    Case(
        message="Simple conjunct query with quoted field and spacing.",
        query='au:del_maestro AND ti:"   dark matter   "',
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, '"dark matter"'),
        ),
    ),
    Case(
        message="Disjunct query with an unary not.",
        query="au:del_maestro OR (ANDNOT ti:checkerboard)",
        phrase=(
            Operator.OR,
            Term(Field.Author, "del_maestro"),
            (Operator.ANDNOT, Term(Field.Title, "checkerboard")),
        ),
    ),
    Case(
        message="Conjunct query with nested disjunct query.",
        query="au:del_maestro ANDNOT (ti:checkerboard OR ti:Pyrochlore)",
        phrase=(
            Operator.ANDNOT,
            Term(Field.Author, "del_maestro"),
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
        ),
    ),
    Case(
        message="Conjunct query with nested disjunct query.",
        query=(
            "((au:del_maestro OR au:bob) "
            "ANDNOT (ti:checkerboard OR ti:Pyrochlore))"
        ),
        phrase=(
            Operator.ANDNOT,
            (
                Operator.OR,
                Term(Field.Author, "del_maestro"),
                Term(Field.Author, "bob"),
            ),
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
        ),
    ),
    Case(
        message="Conjunct ANDNOT query with nested disjunct query.",
        query="(ti:checkerboard OR ti:Pyrochlore) ANDNOT au:del_maestro",
        phrase=(
            Operator.ANDNOT,
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
            Term(Field.Author, "del_maestro"),
        ),
    ),
    Case(
        message="Conjunct AND query with nested disjunct query.",
        query=(
            "(ti:checkerboard OR ti:Pyrochlore) AND "
            "(au:del_maestro OR au:hawking)"
        ),
        phrase=(
            Operator.AND,
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
            (
                Operator.OR,
                Term(Field.Author, "del_maestro"),
                Term(Field.Author, "hawking"),
            ),
        ),
    ),
    Case(
        message="Categories with ORs",
        query=(
            "(cat:a OR cat:b)"
        ),
        phrase=(
            Operator.OR,
            Term(Field.SubjectCategory, "a"),
            Term(Field.SubjectCategory, "b"),
        ),
    ),

]

TEST_PARSE_ERROR_CASES: List[Case] = [
    Case(
        message="Error case with two consecutive operators.",
        query="ti:a or and ti:b",
    ),
    Case(
        message="Error case with two consecutive terms.",
        query="ti:a and ti:b ti:c",
    ),
    Case(
        message="Error case with a trailing operator.",
        query="ti:a and ti:b and",
    ),
    Case(
        message="Error case with a leading operator.", query="or ti:a and ti:b"
    ),
    Case(message="Testing unclosed quote.", query='ti:a and ti:"b'),
    Case(
        message="Testing query string with many problems.",
        query='or ti:a and and ti:"b',
    ),
]

TEST_SERIALIZE_CASES: List[Case] = [
    Case(
        message="Simple query serialization.",
        query="au:copernicus",
        phrase=Term(Field.Author, "copernicus"),
    ),
    Case(
        message="Simple query with quotations.",
        query='ti:"dark matter"',
        phrase=Term(Field.Title, '"dark matter"'),
    ),
    Case(
        message="Simple conjunct query.",
        query="au:del_maestro AND ti:checkerboard",
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "checkerboard"),
        ),
    ),
    Case(
        message="Conjunct query with nested disjunct query.",
        query=(
            "(ti:checkerboard OR ti:Pyrochlore) AND "
            "(au:del_maestro OR au:hawking)"
        ),
        phrase=(
            Operator.AND,
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
            (
                Operator.OR,
                Term(Field.Author, "del_maestro"),
                Term(Field.Author, "hawking"),
            ),
        ),
    ),
]


class TestParsing(TestCase):
    """Testing the classic parser."""

    def test_all_valid_field_values(self):
        for field in Field:
            result = parse_classic_query(f"{field}:some_text")
            self.assertEqual(result, Term(field, "some_text"))

    def test_parse_ok_test_cases(self):
        for case in TEST_PARSE_OK_CASES:
            self.assertEqual(
                parse_classic_query(case.query), case.phrase, msg=case.message
            )

    def test_parse_error_test_cases(self):
        for case in TEST_PARSE_ERROR_CASES:
            with self.assertRaises(BadRequest, msg=case.message):
                parse_classic_query(case.query)

    def test_serialize_cases(self):
        for case in TEST_SERIALIZE_CASES:
            self.assertEqual(
                phrase_to_query_string(case.phrase),
                case.query,
                msg=case.message,
            )
