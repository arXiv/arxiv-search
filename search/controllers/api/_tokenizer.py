from typing import Any, Tuple

from ...domain.api import Phrase, Expression, Term, Operator, Field, Triple
from werkzeug.exceptions import BadRequest

def tokenize(query: str) -> Any:
    # Parser
    tokens = []
    token_start = 0
    paren_group = []

    for i, c in enumerate(query):
        if c == '(':
            paren_group.append(i)
        elif c == ')':
            start = paren_group.pop()
            if not paren_group and start == 0 and i + 1 == len(query):
                # Parent spans whole group, strip the parens, things get weird with parsing...
                return tokenize(query[1:i])
            elif not paren_group:
                tokens.append(tokenize(query[start+1:i])) # pass the paren-stripped phrase
                token_start = i+1
        elif c == ' ':
            if not paren_group and token_start != i:
                tokens.append(query[token_start:i])
                token_start = i + 1
            elif token_start == i:
                token_start = i + 1
        else:
            continue

    if query[token_start:]:
        tokens.append(query[token_start:])

    classed_tokens = []
    for token in tokens:
        if isinstance(token, str):
            if ':' in token:
                token = _parse_field_query(token)
                classed_tokens.append(token)
            else:
                token = _parse_operator(token)
                classed_tokens.append(token)
        else:
            classed_tokens.append(token)

    if len(classed_tokens) == 1:
        return classed_tokens[0]
    else:
        return tuple(classed_tokens)

def _parse_operator(characters: str) -> Operator:
    try:
        return Operator(characters.strip())
    except ValueError as e:
        raise BadRequest(f'Cannot parse fragment: {characters}') from e


def _parse_field_query(field_part: str) -> Tuple[Field, str]:
    field_name, value = field_part.split(':', 1)
    try:
        field = Field(field_name)
    except ValueError as e:
        raise BadRequest(f'Invalid field: {field_name}') from e
    return field, value
