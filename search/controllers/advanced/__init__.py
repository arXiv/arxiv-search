"""
Handle requests to support the advanced search feature.

The primary entrypoint to this module is :func:`.search`, which handles
GET requests to the author search endpoint. It uses
:class:`.AdvancedSearchForm` to generate form HTML, validate request
parameters, and produce informative error messages for the user.
"""

import re
from http import HTTPStatus
from typing import Tuple, List, Dict, Any, Optional
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from flask import url_for
from werkzeug.datastructures import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import BadGateway, InternalServerError, BadRequest, NotFound


from arxiv import taxonomy
import logging

from search.services import index, SearchSession
from search.domain import (
    AdvancedQuery,
    FieldedSearchTerm,
    DateRange,
    Classification,
    FieldedSearchList,
    ClassificationList,
    Query,
)
from search import consts
from search.controllers.advanced import forms
from search.controllers.util import paginate, catch_underscore_syntax


logger = logging.getLogger(__name__)


Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


TERM_FIELD_PTN = re.compile(r"terms-([0-9])+-term")


def search(request_params: MultiDict) -> Response:
    """
    Perform a search from the advanced search interface.

    This is intended to support ONLY form-based search, to replace the classic
    advanced search view.

    Parameters
    ----------
    request_params : dict

    Returns
    -------
    dict
        Response content.
    int
        HTTP status code.
    dict
        Extra headers to add to the response.

    Raises
    ------
    InternalServerError
        Raised when there is an unrecoverable error while interacting with the
        search index.

    """
    # We may need to intervene on the request parameters, so we'll
    # reinstantiate as a mutable MultiDict.
    if isinstance(request_params, ImmutableMultiDict):
        request_params = MultiDict(request_params.items(multi=True))

    logger.debug("search request from advanced form")
    response_data: Dict[str, Any] = {}
    response_data["show_form"] = "advanced" not in request_params
    logger.debug("show_form: %s", str(response_data["show_form"]))

    # Here we intervene on the user's query to look for holdouts from
    # the classic search system's author indexing syntax (surname_f). We
    # rewrite with a comma, and show a warning to the user about the
    # change.
    has_classic = False
    for key, value in request_params.items():
        if value is None:
            continue
        match = TERM_FIELD_PTN.search(key)
        if match is None:
            continue
        value = str(value)
        i = match.group(1)
        field = request_params.get(f"terms-{i}-field")
        # We are only looking for this syntax in the author search, or
        # in an all-fields search.
        if field not in ["all", "author"]:
            continue

        value, _has_classic = catch_underscore_syntax(value)
        has_classic = _has_classic if not has_classic else has_classic
        request_params.setlist(key, [value])

    response_data["has_classic_format"] = has_classic
    form = forms.AdvancedSearchForm(request_params)
    q: Optional[Query]
    # We want to avoid attempting to validate if no query has been entered.
    #  If a query was actually submitted via the form, 'advanced' will be
    #  present in the request parameters.
    if "advanced" in request_params:

        if form.validate():
            logger.debug("form is valid")
            q = _query_from_form(form)

            # Pagination is handled outside of the form.
            q = paginate(q, request_params)

            try:
                # Execute the search. We'll use the results directly in
                #  template rendering, so they get added directly to the
                #  response content. asdict(
                response_data.update(SearchSession.search(q))  # type: ignore
            except index.IndexConnectionError as ex:
                raise BadGateway(
                    "There was a problem connecting to the search index. This "
                    "is quite likely a transient issue, please try your "
                    "search again. If this problem persists, please report it "
                    "to help@arxiv.org."
                ) from ex
            except index.QueryError as ex:
                raise BadRequest(
                    "There was a problem executing your query. Please try "
                    "a different query. If this problem persists, please "
                    "report it to help@arxiv.org."
                ) from ex
            except index.OutsideAllowedRange as ex:
                raise BadRequest(
                    "You can't get results in that range."
                ) from ex
            except Exception as ex:
                logger.error("Unhandled exception: %s", str(ex))
                raise InternalServerError(
                    "There was a problem. If this problem persists, "
                    "please report it to help@arxiv.org."
                ) from ex
            response_data["query"] = q
        else:
            logger.debug("form is invalid: %s", str(form.errors))
            if "order" in form.errors or "size" in form.errors:
                # It's likely that the user tried to set these parameters
                # manually, or that the search originated from somewhere else
                # (and was configured incorrectly).
                advanced_url = url_for("ui.advanced_search")
                raise BadRequest(
                    f"It looks like there's something odd about your search"
                    f" request. Please try <a href='{advanced_url}'>starting"
                    f" over</a>."
                )

            # Force the form to be displayed, so that we can render errors.
            #  This has most likely occurred due to someone manually crafting
            #  a GET response, but it could be something else.
            response_data["show_form"] = True

    # We want the form handy even when it is not shown to the user. For
    #  example, we can generate new form-friendly requests to update sort
    #  order and page size by embedding the form (hidden).
    response_data["form"] = form
    headers={}
    headers["Surrogate-Control"]="max-age=600"
    return response_data, HTTPStatus.OK, headers


def _query_from_form(form: forms.AdvancedSearchForm) -> AdvancedQuery:
    """
    Generate a :class:`.AdvancedQuery` from valid :class:`.AdvancedSearchForm`.

    Parameters
    ----------
    form : :class:`.AdvancedSearchForm`
        Presumed to be filled and valid.

    Returns
    -------
    :class:`.AdvancedQuery`

    """
    q = AdvancedQuery()
    q = _update_query_with_dates(q, form.date.data)
    q = _update_query_with_terms(q, form.terms.data)
    q = _update_query_with_classification(q, form.classification.data)
    q.include_cross_list = (
        form.classification.include_cross_list.data
        == form.classification.INCLUDE_CROSS_LIST
    )
    if form.include_older_versions.data:
        q.include_older_versions = True
    order = form.order.data
    if order and order != "None":
        q.order = order
    q.hide_abstracts = form.abstracts.data == form.HIDE_ABSTRACTS
    return q


def _update_query_with_classification(
    q: AdvancedQuery, data: MultiDict
) -> AdvancedQuery:
    q.classification = ClassificationList()
    archives = [
        ("computer_science", "cs"),
        ("economics", "econ"),
        ("eess", "eess"),
        ("mathematics", "math"),
        ("q_biology", "q-bio"),
        ("q_finance", "q-fin"),
        ("statistics", "stat"),
    ]
    for field, archive in archives:
        if data.get(field):
            # Fix for these typing issues is coming soon!
            #  See: https://github.com/python/mypy/pull/4397
            q.classification.append(
                Classification(archive={"id": archive})  # type: ignore
            )
    if data.get("physics") and "physics_archives" in data:
        if "all" in data["physics_archives"]:
            q.classification.append(
                Classification(group={"id": "grp_physics"})  # type: ignore
            )
        else:
            q.classification.append(
                Classification(  # type: ignore
                    group={"id": "grp_physics"},
                    archive={"id": data["physics_archives"]},
                )
            )
    return q


# FIXME: Argument type.
def _update_query_with_terms(
    q: AdvancedQuery, terms_data: List[Any]
) -> AdvancedQuery:
    q.terms = FieldedSearchList(
        [
            FieldedSearchTerm(**term)  # type: ignore
            for term in terms_data
            if term["term"]
        ]
    )
    return q


def _update_query_with_dates(
    q: AdvancedQuery, date_data: MultiDict
) -> AdvancedQuery:
    filter_by = date_data["filter_by"]
    if filter_by == "all_dates":  # Nothing to do; all dates by default.
        return q
    elif filter_by == "past_12":
        one_year_ago = date.today() - relativedelta(months=12)
        # Fix for these typing issues is coming soon!
        #  See: https://github.com/python/mypy/pull/4397
        q.date_range = DateRange(  # type: ignore
            start_date=datetime(
                year=one_year_ago.year,
                month=one_year_ago.month,
                day=1,
                hour=0,
                minute=0,
                second=0,
                tzinfo=consts.EASTERN,
            )
        )
    elif filter_by == "specific_year":
        q.date_range = DateRange(  # type: ignore
            start_date=datetime(
                year=date_data["year"].year,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                tzinfo=consts.EASTERN,
            ),
            end_date=datetime(
                year=date_data["year"].year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                tzinfo=consts.EASTERN,
            ),
        )
    elif filter_by == "date_range":
        if date_data["from_date"]:
            date_data["from_date"] = datetime.combine(  # type: ignore
                date_data["from_date"],
                datetime.min.time(),
                tzinfo=consts.EASTERN,
            )
        if date_data["to_date"]:
            date_data["to_date"] = datetime.combine(  # type: ignore
                date_data["to_date"],
                datetime.min.time(),
                tzinfo=consts.EASTERN,
            )

        q.date_range = DateRange(  # type: ignore
            start_date=date_data["from_date"], end_date=date_data["to_date"]
        )

    if q.date_range:
        q.date_range.date_type = date_data["date_type"]
    return q


# TODO: this _could_ go on the AdvancedSearchForm or ClassificationForm.
def group_search(args: MultiDict, groups_or_archives: str) -> Response:
    """
    Short-cut for advanced search with group or archive pre-selected.

    Note that this only supports options supported in the advanced search
    interface. Anything else will result in a 404.
    """
    logger.debug("Group search for %s", groups_or_archives)
    valid_archives = []
    for archive in groups_or_archives.split(","):
        if archive not in taxonomy.ARCHIVES:
            logger.debug("archive %s not found in taxonomy", archive)
            continue
        # Support old archives.
        if archive in taxonomy.ARCHIVES_SUBSUMED:
            category = taxonomy.CATEGORIES[taxonomy.ARCHIVES_SUBSUMED[archive]]
            archive = category["in_archive"]
        valid_archives.append(archive)

    if len(valid_archives) == 0:
        logger.debug("No valid archives in request")
        raise NotFound("No such archive.")

    logger.debug("Request for %i valid archives", len(valid_archives))
    args = args.copy()
    for archive in valid_archives:
        fld = dict(forms.ClassificationForm.ARCHIVES).get(archive)
        if fld is not None:  # Try a top-level archive first.
            args[f"classification-{fld}"] = True
        else:
            # Might be a physics archive; if so, also select the physics
            # group on the form.
            fld = dict(forms.ClassificationForm.PHYSICS_ARCHIVES).get(archive)
            if fld is None:
                logger.warn(f"Invalid archive shortcut: {fld}")
                continue
            args["classification-physics"] = True
            # If there is more than one physics archives, only the last one
            # will be preserved.
            args["classification-physics_archives"] = fld
    return search(args)
