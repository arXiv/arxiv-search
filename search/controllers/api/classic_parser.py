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

    # Iterate through characters
    for i, c in enumerate(query):
        if c == '(':
            paren_group.append(i) # add open paren start position to stack
        elif c == ')':
            start = paren_group.pop() # get innermost open paren
            if not paren_group and start == 0 and i + 1 == len(query):
                # Parent spans whole group, strip the parens and just return the de-parened phrase
                return _tokenize_query_string(query[1:i])
            elif not paren_group:
                # pass the paren-stripped phrase for parsing
                tokens.append(parse_classic_query(query[start+1:i]))
                token_start = i+1
        elif c == '"':
            in_quote = not in_quote # flip quotation bit
        elif c == ' ':
            if in_quote:
                continue # keep moving if parsing a quote
            elif not paren_group and token_start != i:
                tokens.append(query[token_start:i]) # append the token
                token_start = i + 1
            elif token_start == i:
                token_start = i + 1 # multiple spaces, move the token_start back
        else:
            continue

    # handle final-position token
    if query[token_start:]:
        tokens.append(query[token_start:])

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
    for token in classed_tokens:
        if isinstance(token, Operator):
            current_op = token
        else:
            if current_op:
                token = (current_op, token)
            phrases.append(token)

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

    # cast field to Field enum
    try:
        field = Field(field_name)
    except ValueError as e:
        raise BadRequest(f'Invalid field: {field_name}') from e

    # process quotes, if present
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    return field, value
