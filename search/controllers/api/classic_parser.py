"""
Utility module for Classic API Query parsing.

We use a recursive descent parser, implemented via :func:`parse_classic_query`.

Tokens are themselves parsed using two helpers: :func:`_parse_operator` and
:func:`_parse_field_query`.

The final, parsed query is a :class:`domain.api.Phrase`, which is a nested
set of Tuples::

    >>> parse_classic_query("au:del_maestro AND ti:checkerboard")
    ((Field.Author, 'del_maestro'), Operator.AND, (Field.Title, 'checkerboard'))

See :module:`tests.test_classic_parser` for more examples.
"""


from typing import Any, List, Optional, Tuple, Union
from operator import attrgetter

from werkzeug.exceptions import BadRequest

from ...domain.api import Phrase, Operator, Field, Term

def parse_classic_query(query: str) -> Phrase:
    """
    Parse Classic API-style query string into app-native Phrase.

    Iterates through each character in the string, applying a recursive-descent
    parser and appropriately handling parens and quotes.

    It iterates through each character:
    1.  If a paren group is opened, we append to a list of start positions for
        open paren groups.
    2.  If a paren is closed, we pop out the most recent open paren from the 
        stack of start positions and recursively parse the paren group, adding
        it to our list of tokens.
    3.  If a quote is opened, flip a quotation flag.
    4.  If a space is encountered, append the token to the list of tokens and
        reset the token start position.

    Parameters
    ----------
    query : str
        A Classic API query string.

    Returns
    -------
    :class:`Phrase`
        A tuple representing the query.

    """
    return _group_tokens(_cast_tokens(_tokenize_query_string(query)))


def _tokenize_query_string(query: str) -> List[Union[str, Phrase]]:
    """Tokenizes query string into list of strings and sub-Phrases."""
    # Intializing state variables
    tokens: List[Union[str, Phrase]] = []
    token_start = 0
    paren_group = []
    in_quote = False

    for i, c in enumerate(query):
        if c == '(':
            paren_group.append(i)  # Add open paren start position to stack.
        elif c == ')':
            start = paren_group.pop()  # Get innermost open paren.
            if not paren_group and start == 0 and i + 1 == len(query):
                # Paren spans whole group, strip the parens and just return the de-parened phrase.
                return _tokenize_query_string(query[1:i])
            elif not paren_group:
                # Pass the paren-stripped phrase for parsing.
                tokens.append(parse_classic_query(query[start + 1:i]))
                token_start = i+1
        elif c == '"':
            in_quote = not in_quote  # Flip quotation bit.
        elif c == ' ':
            if in_quote:
                continue  # Keep moving if parsing a quote.
            elif not paren_group and token_start != i:
                tokens.append(query[token_start:i])
                token_start = i + 1
            elif token_start == i:
                token_start = i + 1  # Multiple spaces, move the token_start back.
        else:
            continue

    # As the final token does not end with a ' ', process it here.
    if query[token_start:]:
        tokens.append(query[token_start:])

    # Handle unclosed quotation mark.
    if in_quote:
        raise BadRequest(f'Quotation does not close: {query[token_start:]}')

    return tokens


def _cast_tokens(tokens: List[Union[str, Phrase]]) -> List[Union[Operator, Term, Phrase]]:
    """Cast tokens to class-based representations."""
    classed_tokens: List[Union[Operator, Term, Phrase]] = []
    for token in tokens:
        if isinstance(token, str):
            if ':' in token:
                token = _parse_field_query(token)
                classed_tokens.append(token)
            else:
                operator = _parse_operator(token)
                classed_tokens.append(operator)
        else:
            classed_tokens.append(token)

    return classed_tokens


def _group_tokens(classed_tokens: List[Union[Operator, Term, Phrase]]) -> Phrase:
    """Group operators together with Term."""
    phrases: List[Phrase] = []
    current_op: Optional[Operator] = None
    prev_token: Optional[Union[Operator, Term, Phrase]] = None
    for token in classed_tokens:
        if isinstance(token, Operator) and isinstance(prev_token, Operator):
            raise BadRequest(f'Query contains 2 consecutive operators: {prev_token} {token}')
        if isinstance(token, Operator):
            current_op = token
        else:
            if current_op:
                token = (current_op, token)
            phrases.append(token)
        prev_token = token

    # Return single-token query, otherwise cast to a tuple.
    if len(phrases) == 1:
        return phrases[0]
    else:
        # When mypy adds full support for recursive types, this should be fine.
        return tuple(phrases)  # type: ignore


def _parse_operator(characters: str) -> Operator:
    try:
        return Operator(characters.strip())
    except ValueError as e:
        raise BadRequest(f'Cannot parse fragment: {characters}') from e


def _parse_field_query(field_part: str) -> Term:
    field_name, value = field_part.split(':', 1)

    # Cast field to Field enum.
    try:
        field = Field(field_name)
    except ValueError as e:
        raise BadRequest(f'Invalid field: {field_name}') from e

    # Process leading and trailing whitespace and quotes, if present.
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    return field, value


def phrase_to_query_string(phrase: Phrase) -> str:
    """Converts a phrase object back to a query string."""
    parts: List[str] = []
    for token in phrase:
        if isinstance(token, Operator):
            parts.append(token.value)
        elif isinstance(token, Field):
            parts.append(f"{token.value}:")
        elif isinstance(token, str):
            # Strings are added to the field or operator preceeding it.
            if ' ' in token:
                parts[-1] += f'"{token}"'
            else:
                parts[-1] += token
        elif isinstance(token, tuple):
            part = phrase_to_query_string(token)
            # If the returned part is a Phrase, add parens.
            if ' ' in part and part.count(':') > 1 \
                    and part.split()[0] not in map(attrgetter('value'), Operator):  # Doesn't start with an operator.
                part = f'({part})'
    
            parts.append(part)
        else:
            raise ValueError(f"Invalid token in phrase: {token}")
    
    return ' '.join(parts)
