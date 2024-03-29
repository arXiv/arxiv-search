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
from typing import Tuple, List, Optional

from lark import Lark, Transformer, Token
from werkzeug.exceptions import BadRequest

from search.domain.base import Operator, Field, Term, Phrase


class QueryTransformer(Transformer):
    """AST builder class.

    This class will be used to traverse the AST generated by the LARK parser
    and transform it's tokens to our AST representation.

    Classic query phrase can be either a::

        - Term - just a single term. E.e: Term(Field.All, "electron")
        - (Operator,  Phrase) - Unary operation (only ANDNOT is allowed and it
            represent unary negation. I.e:
            (Operator.ANDNOT Term(Field.All, "electron"))
        - (Operator, Phrase, Phrase) - Binary operation (AND, OR, ANDNOT). I.e:
            (
                Operator.AND,
                Term(Field.All, "electron"),
                Term(Field.Author, "john")
            )

    And also any recursive representation of the following structure.

    """

    def field(self, tokens: List[Token]) -> Field:
        """Transform `all`, `au`...field identifiers to `Field` enum values."""
        (f,) = tokens
        return Field(str(f))

    def search_string(self, tokens: List[Token]) -> str:
        """Un-quote a search string and strips it of whitespace.

        This is the actual search string entered after the Field qualifier.
        """
        (s,) = tokens
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        return s.strip() or ""

    def term(self, tokens: List[Token]) -> Term:
        """Construct a Term combining a field and search string."""
        return Term(*tokens)

    def unary_operator(self, tokens: List[Token]) -> Operator:
        """Transform unary operator string to Operator enum value."""
        (u,) = tokens
        return Operator(str(u))

    def unary_expression(self, tokens: List[Token]) -> Tuple[Operator, Phrase]:
        """Create a unary operation tuple."""
        return tokens[0], tokens[1]

    def binary_operator(self, tokens: List[Token]) -> Operator:
        """Transform binary operator string to Operator enum value."""
        (b,) = tokens
        return Operator(str(b))

    def binary_expression(
        self, tokens: List[Token]
    ) -> Tuple[Operator, Phrase, Phrase]:
        """Create a binary operation tuple."""
        return tokens[1], tokens[0], tokens[2]

    def expression(self, tokens: List[Token]) -> Phrase:
        """Do nothing, expression is already a singular value."""
        return tokens[0]  # type:ignore

    def empty(self, tokens: List[Token]) -> Term:
        """Return empty term for an empty string."""
        return Term(Field.All)

    def query(self, tokens: List[Token]) -> Phrase:
        """Query is just an expression which is a singular value."""
        return tokens[0]  # type:ignore


QUERY_PARSER = Lark(
    fr"""
    query : expression
          | empty

    empty : //

    expression : term
               | "(" expression ")"
               | unary_expression
               | binary_expression

    term : field ":" search_string
    field : /{"|".join(Field)}/
    search_string : /[^\s\"\(\)]+/ | ESCAPED_STRING

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


def parse_classic_query(query: str) -> Optional[Phrase]:
    """Parse the classic query."""
    try:
        return QUERY_PARSER.parse(query)  # type:ignore
    except Exception:
        raise BadRequest(f"Invalid query string: '{query}'")
    return


def phrase_to_query_string(phrase: Phrase, depth: int = 0) -> Optional[str]:
    """Convert a Phrase to a query string."""
    if isinstance(phrase, Term):
        return (
            f"{phrase.field}:{phrase.value}"
            if re.search(r"\s", phrase.value) is None
            else f'{phrase.field}:"{phrase.value}"'
        )
    elif len(phrase) == 2:
        unary_op, exp = phrase[:2]
        value = f"{unary_op.value} {phrase_to_query_string(exp, depth+1)}"
        return f"({value})" if depth != 0 else value
    elif len(phrase) == 3:
        binary_op, exp1, exp2 = phrase[:3]  # type:ignore
        value = (
            f"{phrase_to_query_string(exp1, depth+1)} "
            f"{binary_op.value} "
            f"{phrase_to_query_string(exp2, depth+1)}"
        )
        return f"({value})" if depth != 0 else value
    return None
