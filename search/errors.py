class SearchError(Exception):
    def __init__(self, message: str):
        self.message = message

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return f"{self.name}({self.message})"

    __repr__ = __str__


class ValidationError(SearchError):
    def __init__(
        self, message: str, link: str = "http://arxiv.org/api/errors"
    ):
        super().__init__(message=message)
        self.link = link
