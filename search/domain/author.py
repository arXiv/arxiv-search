from search.domain import Query, Property, Base


class Author(Base):
    forename = Property('forename', str)
    surname = Property('forensurnameame', str)

    def __str__(self):
        if self.forename:
            return f'{self.forename} {self.surname}'
        return self.surname
            

class AuthorList(list):
    def __str__(self):
        return ', '.join([str(au) for au in self])


class AuthorQuery(Query):
    """Represents an author query."""

    authors = Property('authors', AuthorList)
