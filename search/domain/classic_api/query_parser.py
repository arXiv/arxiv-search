"""
Utility module for Classic API Query parsing.

Uses lark-parser (EBNF parser) [1].
[1]: https://github.com/lark-parser/lark/blob/master/README.md


The final, parsed query is a :class:`domain.api.Phrase`, which is a nested
set of Tuples::

    >>> parse_classic_query("au:del_maestro AND ti:checkerboard")
    (
        Operator.AND,
        Term(field=Field.Author, value='del_maestro'),
        Term(field=Field.Title, value='checkerboard')
    )

See :module:`tests.test_query_parser` for more examples.
"""
import re

from lark import Lark, Transformer
from werkzeug.exceptions import BadRequest

from search.domain.base import Operator, Field, Term, Phrase


class QueryTransformer(Transformer):
    def string(self, tokens):
        (s,) = tokens
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        return s.strip()

    def field(self, tokens):
        (f,) = tokens
        return Field(str(f))

    def term(self, tokens):
        return Term(*tokens)

    def unary_operator(self, tokens):
        (u,) = tokens
        return Operator(str(u))

    def unary_expression(self, tokens):
        return tokens[0], tokens[1]

    def binary_operator(self, tokens):
        (b,) = tokens
        return Operator(str(b))

    def binary_expression(self, tokens):
        return tokens[1], tokens[0], tokens[2]

    def expression(self, tokens):
        return tokens[0]

    def empty(self, tokens):
        return None

    def query(self, tokens):
        return tokens[0]


QUERY_PARSER = Lark(
    fr"""
    query : expression
          | empty

    empty : //

    expression : term
               | "(" expression ")"
               | unary_expression
               | binary_expression

    term : field ":" string
    field : /{"|".join(Field)}/
    string : /[^\s\"\(\)]+/ | ESCAPED_STRING

    unary_operator : /ANDNOT/
    unary_expression : unary_operator expression

    binary_operator : /(ANDNOT|AND|OR)/
    binary_expression : expression binary_operator expression

    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS

    """,
    start="query",
    parser="lalr",
    transformer=QueryTransformer(),
)


def parse_classic_query(query: str) -> Phrase:
    try:
        return QUERY_PARSER.parse(query)
    except Exception:
        raise BadRequest()


def phrase_to_query_string(phrase: Phrase, depth=0):
    if phrase is None:
        return ""

    if isinstance(phrase, Term):
        return (
            f"{phrase.field}:{phrase.value}"
            if re.search(r"\s", phrase.value) is None
            else f'{phrase.field}:"{phrase.value}"'
        )
    elif len(phrase) == 2:
        unary_op, exp = phrase
        value = f"{unary_op.value} {phrase_to_query_string(exp, depth+1)}"
        return f"({value})" if depth != 0 else value
    elif len(phrase) == 3:
        binary_op, exp1, exp2 = phrase
        value = (
            f"{phrase_to_query_string(exp1, depth+1)} "
            f"{binary_op.value} "
            f"{phrase_to_query_string(exp2, depth+1)}"
        )
        return f"({value})" if depth != 0 else value
