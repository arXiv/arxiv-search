"""Query-builders and helpers for searching by author name."""

from typing import Tuple, Optional, List
from elasticsearch_dsl import Search, Q, SF
from .util import wildcardEscape, is_literal_query, Q_


def _parseName(au_safe: str) -> Tuple[str, Optional[str]]:
    """Parse a name string into its (likely) constituent parts."""
    # We interpret the comma as separating the surname from the forename.
    if "," in au_safe:
        au_parts = au_safe.split(',')
        if len(au_parts) >= 2:
            surname = au_parts[0]
            forename = au_parts[1]
            return surname.strip(), forename.strip()

    # Otherwise, treat the last word in the name as the surname. This isn't
    # a great approach from first principles, but it produces reasonable
    # results in practice.
    term_parts = au_safe.split()
    if len(term_parts) > 1:
        return term_parts[-1], ' '.join(term_parts[:-1])
    return au_safe, None


# TODO: once we're happy with the behavior, this can be broken out into smaller
# pieces, for readability.
def construct_author_query(term: str) -> Q:
    """Generate an author name query in the ElasticSearch DSL."""
    _author_q = Q()
    score_functions: List = []

    # Multiple authors can be provided, delimited by commas.
    for au_name in term.split(';'):
        au_name = au_name.strip().lower()

        au_name, has_wildcard = wildcardEscape(au_name)
        au_safe = au_name.replace('*', '').replace('?', '').replace('"', '')
        surname_safe, forename_safe = _parseName(au_safe)
        if forename_safe is not None:
            fullname_safe = f'{forename_safe} {surname_safe}'
        else:
            fullname_safe = surname_safe
        _q = (
            # Matching on keyword field is effectively an exact match.
            Q('match', **{
                'authors__full_name__exact': {
                    'query': fullname_safe, 'boost': 10
                }
            })
            # The next best case is that the query is a substring of
            #  the full name.
            | Q('match_phrase', **{
                'authors__full_name': {'query': fullname_safe, 'boost': 9}
            })
        )
        if not is_literal_query(term):
            # We support wildcards (?*) within each author name. Since
            # ES will treat the non-wildcard part of the term as a literal,
            # we need to apply each word in the name separately.
            if has_wildcard:
                _q_wc = Q()
                for npart in au_name.split():
                    _q_wc &= Q('wildcard', **{
                        'authors__full_name': {
                            'value': npart, 'boost': 8
                        }
                    })
                _q |= _q_wc
            # Otherwise, just do a general text match on the full name
            # as a third-best option. In this case, word order won't
            # matter, but all words in the name must be present.
            else:
                _q |= Q('match', **{
                    'authors__full_name': {
                        'query': fullname_safe,
                        'boost': 8,
                        'operator': 'and'
                    }
                })

        # We want to boost the most relevant results to the top, using
        # the parsed name parts available in the search index.
        score_functions += [
            # Give an extra boost based on how well the query matches
            # the full name.
            SF({
                'weight': 25,
                'filter': Q(
                    "nested", path="authors", query=Q(
                        'match', **{
                            'authors__full_name': fullname_safe
                        }
                    )
                )
            }),
            SF({
                'weight': 20,
                'filter': Q(
                    "nested", path="authors", query=Q(
                        'match', **{
                            'authors__full_name_initialized': au_safe
                        }
                    )
                )
            })
        ]

        if not is_literal_query(au_name):
            # Give an extra boost if the last word of the query is
            # in the parsed last name field.
            score_functions += [
                SF({
                    'weight': 15,
                    'filter': Q(
                        "nested", path="authors", query=Q(
                            'match', **{
                                'authors__last_name': surname_safe
                            }
                        )
                    )
                }),
            ]

        if not is_literal_query(au_name):
            # If the name has more than one word, it likely contains a forename
            # or initials.
            if forename_safe is not None:
                init_forename = ' '.join(
                    [part[0] for part in forename_safe.split()]
                )
                init_name = ' '.join(init_forename.split() + [surname_safe])
                _q |= (
                    Q('match', **{
                        'authors__full_name_initialized__exact': {
                            'query': init_name,
                            'boost': 5
                        }
                    })
                    | Q('match_phrase', **{
                        'authors__full_name_initialized': {
                            'query': init_name,
                            'boost': 4
                        }
                    })
                )

                score_functions += [
                    SF({
                        'weight': 12,
                        'filter': Q(
                            "nested", path="authors", query=Q(
                                "match", **{
                                    "authors__first_name__exact": forename_safe
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 8,
                        'filter': Q(
                            "nested", path="authors", query=Q(
                                "match", **{
                                    "authors__first_name__exact": init_forename
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 10, 'filter': Q(
                            "nested", path="authors", query=Q(
                                "match_phrase", **{
                                    "authors__first_name": forename_safe
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 8, 'filter': Q(
                            "nested", path="authors", query=Q(
                                "match_phrase", **{
                                    "authors__first_name": init_forename
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 1, 'filter': Q(
                            "nested", path="authors", query=Q(
                                "match", **{
                                    "authors__first_name": forename_safe
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 1, 'filter': Q(
                            "nested", path="authors", query=Q(
                                "match", **{
                                    "authors__first_name": init_forename
                                }
                            )
                        )
                    }),
                    SF({
                        'weight': 2, 'filter': Q(
                            "nested", path="authors", query=Q(
                                "match", **{
                                    "authors__initials": init_forename.lower()
                                }
                            )
                        )
                    }),
                ]
        _author_q &= Q("nested", path="authors", query=_q)

    return Q('function_score', query=_author_q,
             score_mode="sum", boost=1, boost_mode='multiply',
             functions=score_functions)


def construct_author_id_query(field: str, term: str) -> Q:
    """Generate a query part for ORCID and Author ID using the ES DSL."""
    return (
        Q("nested", path="authors",
          query=Q_('match', f'authors__{field}', term))
        | Q("nested", path="owners",
            query=Q_('match', f'owners__{field}', term))
        | Q_('match', f'submitter__{field}', term)
    )
