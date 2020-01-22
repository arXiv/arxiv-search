"""Search error classes."""


class SearchError(Exception):
    """Generic search error."""

    def __init__(self, message: str):
        """Initialize the error message."""
        self.message = message

    @property
    def name(self) -> str:
        """Error name."""
        return self.__class__.__name__

    def __str__(self) -> str:
        """Represent error as a string."""
        return f"{self.name}({self.message})"

    __repr__ = __str__


class ValidationError(SearchError):
    """Validation error."""

    def __init__(
        self, message: str, link: str = "http://arxiv.org/api/errors"
    ):
        """Initialize the validation error."""
        super().__init__(message=message)
        self.link = link
