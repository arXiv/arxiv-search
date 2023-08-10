"""Query-builders and helpers for searching by author name."""

import re
from functools import reduce
from operator import ior, iand

from elasticsearch_dsl import Q

import logging

from search.services.index.util import escape, STRING_LITERAL, has_wildcard

logger = logging.getLogger(__name__)
logger.propagate = False

# We don't remove stopwords from author names at index time because
# institutions and collaborations are often treated as authors just like
# people.
STOP = ["and", "or", "the", "of", "a", "for"]


def _remove_stopwords(term: str) -> str:
    """Remove common stopwords, except in literal queries."""
    parts = re.split(STRING_LITERAL, term)
    for stopword in STOP:
        parts = [
            re.sub(fr"(^|\s+){stopword}(\s+|$)", " ", part)
            if not part.startswith('"') and not part.startswith("'")
            else part
            for part in parts
        ]
    return "".join(parts)


def Q_(qtype: str, field: str, value: str) -> Q:
    """Generate an appropriate :class:`Q` based on wildcard presence."""
    if has_wildcard(value):
        return Q("wildcard", **{field: {"value": escape(value)}})
    return Q(qtype, **{field: escape(value)})


def part_query(term: str, path: str = "authors") -> Q:
    """
    Build a query that matches within a single author using name parts.

    Anything before the first comma is treated as the author's surname, and
    everything after the first comma is treated as the author's first name
    or initials.

    Parameters
    ----------
    term : str
        Search term for a single author.
    path : str
        Nested document path.

    Returns
    -------
    :class:`.Q`

    """
    AUTHOR_QUERY_FIELDS = [
        f"{path}.full_name",
        f"{path}.last_name",
        f"{path}.full_name_initialized",
    ]
    term = term.strip()
    logger.debug(f"{path} part_query for {term}")

    # Commas are used to distinguish surname and forename.
    forename_is_individuated = "," in term
    if forename_is_individuated:
        # We treat the entire part as a search for a single author. The part
        # before the comma is treated as a surname, and the part after the
        # comma is treated as a forename or a prefix of the forename.
        name_parts = [p.strip() for p in term.split(",")]
        surname = name_parts[0].strip()
        forename = " ".join(name_parts[1:]).strip()

        # Doing a query string so that wildcards and literals are just handled.
        q_surname = Q(
            "query_string",
            fields=[f"{path}.last_name"],
            query=escape(surname),
            default_operator="AND",
            allow_leading_wildcard=False,
        )

        if forename:
            # If a wildcard is provided in the forename, we treat it as a
            # query string query. This has the disadvantage of losing term
            # order, but the advantage of handling wildcards as expected.
            logger.debug(f"Forename: {forename}")
            if has_wildcard(forename):
                q_forename = Q(
                    "query_string",
                    fields=[f"{path}.first_name"],
                    query=escape(forename),
                    auto_generate_phrase_queries=True,
                    default_operator="AND",
                    allow_leading_wildcard=False,
                )

            # Otherwise, we expect the forename to match as a phrase. The
            # _prefix bit means that the last word can match as a prefix of the
            # corresponding term.
            else:
                q_forename = Q(
                    "match_phrase_prefix", **{f"{path}__first_name": forename}
                )

            # It may be the case that the forename consists of initials or some
            # other prefix/partial forename. For a match of this kind, each
            # part of the forename part must be a prefix of a term in the
            # forename.
            if path == "authors" and forename:
                logger.debug("Consider initials: %s", forename)
                q_forename |= Q(
                    "match_phrase_prefix", **{f"{path}__initials": forename}
                )

            # We will treat this as a search for a single author; surname and
            # forename parts must match in the same (nested) author.
            q = q_surname & q_forename
        else:
            q = q_surname
    else:
        # Match across all fields within a single author. We don't know which
        # bits of the query match which bits of the author name. This will
        # handle wildcards, literals, etc.
        q = Q(
            "query_string",
            fields=AUTHOR_QUERY_FIELDS,
            default_operator="AND",
            allow_leading_wildcard=False,
            type="cross_fields",
            query=escape(term),
        )
    return Q("nested", path=path, query=q, score_mode="sum")


def string_query(term: str, path: str = "authors", operator: str = "AND") -> Q:
    """Build a query that handles query strings within a single author."""
    q = Q(
        "query_string",
        fields=[f"{path}.full_name"],
        default_operator=operator,
        allow_leading_wildcard=False,
        type="cross_fields",
        query=escape(term),
    )
    return Q("nested", path=path, query=q, score_mode="sum")


def author_query(term: str, operator: str = "and") -> Q:
    """
    Construct a query based on author (and owner) names.

    Substrings delimited by semicolons should only match if the terms in that
    substring match within a single author.

    If a substring (delimited or not) contains a comma, everything before the
    first comma will be treated as a surname, and the remainder treated as
    either the forename or initials. In this scenario, all terms must match
    within a single author.

    Otherwise, we will simply match all of the parts of the query across all
    of the available author/owner fields. Each part of the query must match in
    at least one field in at least one author/owner.

    Parameters
    ----------
    term: str
        Raw querystring. Should not be escaped or normalized in any way.
    operator : str
        Default: 'AND'; anything else treated as 'OR'. If 'OR', relaxes the
        requirement that all parts of the query match. This is useful for
        "all fields" searches, in which only part of the query may be expected
        to match on an author/owner name.

    Returns
    -------
    :class:`.Q`
        An Elasticsearch DSL query part.

    """
    logger.debug(f"Author query for {term}")
    term = term.lower()

    # Check for balanced double-quotes.
    if '"' in term and term.count('"') % 2 == 0:  # Probably a literal search.
        logger.debug(f"Contains literal: {term}")

        # Apply literal parts of the query separately.
        return reduce(
            iand if operator.upper() == "AND" else ior,
            [
                (
                    string_query(part, operator=operator)
                    | string_query(part, path="owners", operator=operator)
                )
                for part in re.split(STRING_LITERAL, term)
                if part.strip()
            ],
        )

    term = term.replace('"', "")  # Just ignore unbalanced quotes.

    if ";" in term:  # Authors are individuated.
        logger.debug(f"Authors are individuated: {term}")
        logger.debug(f"Operator: {operator}")
        return reduce(
            iand if operator.upper() == "AND" else ior,
            [
                (part_query(author_part) | part_query(author_part, "owners"))
                for author_part in term.split(";")
                if author_part
            ],
        )

    if "," in term:  # Forename is individuated.
        logger.debug(f"Forename is individuated: {term}")
        return part_query(term) | part_query(term, "owners")

    logger.debug(f"General author search: {term}")

    # We include both w/in author and among author matches, so that more
    # precise matches get more weight.
    #
    # A query_string query on the combined field will yield matches among
    # authors.
    q = Q(
        "query_string",
        fields=["authors_combined"],
        query=escape(term, quotes=True),
        default_operator="and",
    )

    # A nested query_string query on full name will match within individual
    # authors.
    q |= Q(
        "nested",
        path="authors",
        score_mode="sum",
        query=Q(
            "query_string",
            fields=["authors.full_name"],
            default_operator=operator,
            allow_leading_wildcard=False,
            query=escape(term, quotes=True),
        ),
    ) | Q(
        "nested",
        path="owners",
        score_mode="sum",
        query=Q(
            "query_string",
            fields=["owners.full_name"],
            default_operator=operator,
            allow_leading_wildcard=False,
            query=escape(term, quotes=True),
        ),
    )
    return q


def author_id_query(term: str, operator: str = "and") -> Q:
    """Generate a query part for Author ID using the ES DSL."""
    term = term.lower()  # Just in case.
    if operator == "or":
        return Q(
            "nested",
            path="owners",
            query=Q("terms", **{"owners__author_id": term.split()}),
        ) | Q("terms", **{"submitter__author_id": term.split()})
    return reduce(
        iand,
        [
            (
                Q(
                    "nested",
                    path="owners",
                    query=Q("term", **{"owners__author_id": part}),
                )
                | Q("term", **{"submitter__author_id": part})
            )
            for part in term.split()
        ],
    )


def orcid_query(term: str, operator: str = "and") -> Q:
    """Generate a query part for ORCID ID using the ES DSL."""
    if operator == "or":
        return Q(
            "nested",
            path="owners",
            query=Q("terms", **{"owners__orcid": term.split()}),
        ) | Q("terms", **{"submitter__orcid": term.split()})
    return reduce(
        iand,
        [
            (
                Q(
                    "nested",
                    path="owners",
                    query=Q("term", **{"owners__orcid": part}),
                )
                | Q("term", **{"submitter__orcid": part})
            )
            for part in term.split()
        ],
    )
