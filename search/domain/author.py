"""Representations of authors, author lists, and author queries."""
from dataclasses import dataclass
from typing import NamedTuple

from search.domain import Query

@dataclass
class Author:
    """Represents an author."""

    forename: str
    surname: str
    fullname: str

    # TODO: gawd this is ugly.
    def __str__(self) -> str:
        """Print the author name."""
        if self.fullname and self.surname:
            if self.forename:
                name = f'{self.forename}[f] {self.surname}[s]'
            else:
                name = f'{self.surname}[s]'
            name = f'{name} OR {self.fullname}'
        elif self.fullname:
            name = self.fullname
        else:
            if self.forename:
                name = f'{self.forename}[f] {self.surname}[s]'
            else:
                name = f'{self.surname}[s]'
        return name


class AuthorList(list):
    """Represents a list of authors."""

    def __str__(self) -> str:
        """Prints comma-delimited list of authors."""
        if len(self) == 0:
            return ''
        if len(self) > 1:
            return ' AND '.join([f"({str(au)})" for au in self])
        return str(self[0])

@dataclass
class AuthorQuery(Query):
    """Represents an author query."""

    authors: AuthorList
