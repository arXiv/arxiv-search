"""Controller for search API requests."""

from typing import Tuple, Dict, Any, Optional, Union
from mypy_extensions import TypedDict
from pytz import timezone
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest, NotFound

from arxiv import status
from arxiv.base import logging
from arxiv.identifier import parse_arxiv_id

from search.services import index
from search.domain.api import Phrase
from search.errors import ValidationError
from search.domain import Query, DocumentSet, ClassicAPIQuery
from search.controllers.classic.classic_parser import parse_classic_query


logger = logging.getLogger(__name__)
EASTERN = timezone("US/Eastern")

SearchResponseData = TypedDict(
    "SearchResponseData",
    {"results": DocumentSet, "query": Union[Query, ClassicAPIQuery]},
)


def query(params: MultiDict) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a search request from the Clasic API.

    First, the method maps old request parameters to new parameters:
    - search_query -> query
    - start -> start
    - max_results -> size

    Then the request is passed to :method:`search()` and returned.

    If ``id_list`` is specified in the parameters and ``search_query`` is
    NOT specified, then each request is passed to :method:`paper()` and
    results are aggregated.

    If ``id_list`` is specified AND ``search_query`` is also specified,
    then the results from :method:`search()` are filtered by ``id_list``.

    Parameters
    ----------
    params : :class:`MultiDict`
        GET query parameters from the request.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.

    Raises
    ------
    :class:`BadRequest`
        Raised when the search_query and id_list are not specified.
    """
    params = params.copy()

    # Parse classic search query.
    raw_query = params.get("search_query")
    if raw_query:
        phrase: Optional[Phrase] = parse_classic_query(raw_query)
    else:
        phrase = None

    # Parse id_list.
    id_list = params.get("id_list", "")
    if id_list:
        id_list = id_list.split(",")
        # Check arxiv id validity
        for arxiv_id in id_list:
            try:
                parse_arxiv_id(arxiv_id)
            except ValueError:
                raise ValidationError(
                    message="incorrect id format for {}".format(arxiv_id),
                    link=("http://arxiv.org/api/errors#"
                          "incorrect_id_format_for_{}").format(arxiv_id)
                )
    else:
        id_list = None

    # Parse result size.
    try:
        max_results = int(params.get("max_results", 50))
    except ValueError:
        raise ValidationError(
            message="max_results must be an integer",
            link="http://arxiv.org/api/errors#max_results_must_be_an_integer",
        )
    if max_results < 0:
        raise ValidationError(
            message="max_results must be non-negative",
            link="http://arxiv.org/api/errors#max_results_must_be_non-negative"
        )

    # Parse result start point.
    try:
        start = int(params.get("start", 0))
    except ValueError:
        raise ValidationError(
            message="start must be an integer",
            link="http://arxiv.org/api/errors#start_must_be_an_integer"
        )
    if start < 0:
        raise ValidationError(
            message="start must be non-negative",
            link="http://arxiv.org/api/errors#start_must_be_non-negative"
        )

    try:
        query = ClassicAPIQuery(
            phrase=phrase, id_list=id_list, size=max_results, page_start=start
        )
    except ValueError:
        raise BadRequest(
            "Either a search_query or id_list must be specified"
            " for the classic API."
        )

    # pass to search indexer, which will handle parsing
    document_set: DocumentSet = index.SearchSession.current_session().search(
        query
    )
    data: SearchResponseData = {"results": document_set, "query": query}
    logger.debug(
        "Got document set with %i results", len(document_set["results"])
    )

    # bad mypy inference on TypedDict and the status code
    return data, status.HTTP_200_OK, {}  # type:ignore


def paper(paper_id: str) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a request for paper metadata from the API.

    Parameters
    ----------
    paper_id : str
        arXiv paper ID for the requested paper.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.

    Raises
    ------
    :class:`NotFound`
        Raised when there is no document with the provided paper ID.

    """
    try:
        document = index.SearchSession.current_session().get_document(
            paper_id
        )  # type: ignore
    except index.DocumentNotFound as e:
        logger.error("Document not found")
        raise NotFound("No such document") from e
    return {"results": document}, status.HTTP_200_OK, {}
