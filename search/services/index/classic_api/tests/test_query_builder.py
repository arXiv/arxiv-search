from typing import List
from unittest import TestCase
from dataclasses import dataclass

from elasticsearch_dsl import Q

from search.domain import Field, Operator, Phrase, Term
from search.services.index.classic_api.query_builder import (
    query_builder,
    FIELD_TERM_MAPPING as FTM,
)


@dataclass
class Case:
    message: str
    phrase: Phrase
    query: Q


TEST_CASES: List[Case] = [
    Case(message="Empty query", phrase=Term(Field.All, ""), query=Q()),
    Case(
        message="Empty query in conjunction.",
        phrase=(
            Operator.AND,
            Term(Field.All, ""),
            Term(Field.All, "electron"),
        ),
        query=FTM[Field.All]("electron"),
    ),
    Case(
        message="Double empty query in conjunction.",
        phrase=(Operator.AND, Term(Field.All, ""), Term(Field.All, ""),),
        query=Q(),
    ),
    Case(
        message="Simple query without grouping/nesting.",
        phrase=Term(Field.Author, "copernicus"),
        query=FTM[Field.Author]("copernicus"),
    ),
    Case(
        message="Simple query with quotations.",
        phrase=Term(Field.Title, "dark matter"),
        query=FTM[Field.Title]("dark matter"),
    ),
    Case(
        message="Simple conjunct AND query.",
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "checkerboard"),
        ),
        query=(
            FTM[Field.Author]("del_maestro") & FTM[Field.Title]("checkerboard")
        ),
    ),
    Case(
        message="Simple conjunct OR query.",
        phrase=(
            Operator.OR,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "checkerboard"),
        ),
        query=(
            FTM[Field.Author]("del_maestro") | FTM[Field.Title]("checkerboard")
        ),
    ),
    Case(
        message="Simple conjunct ANDNOT query.",
        phrase=(
            Operator.ANDNOT,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "checkerboard"),
        ),
        query=(
            FTM[Field.Author]("del_maestro")
            & (~FTM[Field.Title]("checkerboard"))
        ),
    ),
    Case(
        message="Simple conjunct query with quoted field.",
        phrase=(
            Operator.AND,
            Term(Field.Author, "del_maestro"),
            Term(Field.Title, "dark matter"),
        ),
        query=(
            FTM[Field.Author]("del_maestro") & FTM[Field.Title]("dark matter")
        ),
    ),
    Case(
        message="Disjunct query with an unary not.",
        phrase=(
            Operator.OR,
            Term(Field.Author, "del_maestro"),
            (Operator.ANDNOT, Term(Field.Title, "checkerboard")),
        ),
        query=(
            FTM[Field.Author]("del_maestro")
            | (~FTM[Field.Title]("checkerboard"))
        ),
    ),
    Case(
        message="Conjunct query with nested disjunct query.",
        phrase=(
            Operator.ANDNOT,
            Term(Field.Author, "del_maestro"),
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
        ),
        query=FTM[Field.Author]("del_maestro")
        & (
            ~(
                FTM[Field.Title]("checkerboard")
                | FTM[Field.Title]("Pyrochlore")
            )
        ),
    ),
    Case(
        message="Conjunct query with nested disjunct query.",
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
        query=(
            (FTM[Field.Author]("del_maestro") | FTM[Field.Author]("bob"))
            & (
                ~(
                    FTM[Field.Title]("checkerboard")
                    | FTM[Field.Title]("Pyrochlore")
                )
            )
        ),
    ),
    Case(
        message="Conjunct ANDNOT query with nested disjunct query.",
        phrase=(
            Operator.ANDNOT,
            (
                Operator.OR,
                Term(Field.Title, "checkerboard"),
                Term(Field.Title, "Pyrochlore"),
            ),
            Term(Field.Author, "del_maestro"),
        ),
        query=(
            (FTM[Field.Title]("checkerboard") | FTM[Field.Title]("Pyrochlore"))
            & (~FTM[Field.Author]("del_maestro"))
        ),
    ),
    Case(
        message="Conjunct AND query with nested disjunct query.",
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
        query=(
            (FTM[Field.Title]("checkerboard") | FTM[Field.Title]("Pyrochlore"))
            & (FTM[Field.Author]("del_maestro") | FTM[Field.Author]("hawking"))
        ),
    ),
]


class TestQueryBuilder(TestCase):
    def test_query_builder(self):
        for case in TEST_CASES:
            self.assertEqual(
                query_builder(case.phrase), case.query, msg=case.message
            )
