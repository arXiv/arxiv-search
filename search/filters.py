"""Template filters for :mod:`search`."""

from operator import attrgetter

from arxiv import taxonomy
from search.domain import Classification, Query


def display_classification(classification: Classification) -> str:
    """Generate a display-friendly label for a classification."""
    group = classification.get("group")
    category = classification.get("category")
    archive = classification.get("archive")
    parts = []
    if group is not None:
        parts.append(
            group.get("name", taxonomy.get_group_display(group["id"]))
        )
    if archive is not None:
        parts.append(
            archive.get("name", taxonomy.get_archive_display(archive["id"]))
        )
    if category is not None:
        parts.append(
            category.get("name", taxonomy.get_category_display(category["id"]))
        )
    return "::".join(parts)


def category_name(classification: Classification) -> str:
    """Get the category display name for a classification."""
    category = classification.get("category")
    if not category:
        raise ValueError("No category")
    return category.get("name", taxonomy.get_category_display(category["id"]))


def display_query(query: Query) -> str:
    """Build a display representation of a :class:`.Query`."""
    _parts = []
    for attr in type(query).__dataclass_fields__.keys():  # type: ignore
        value = attrgetter(attr)(query)
        if not value:
            continue
        if attr == "classification":
            value = ", ".join([display_classification(v) for v in value])
        _parts.append("%s: %s" % (attr, value))
    return "; ".join(_parts)


filters = [
    ("display_classification", display_classification),
    ("category_name", category_name),
    ("display_query", display_query),
]
