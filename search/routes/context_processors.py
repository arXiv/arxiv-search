"""Context processors for use in :mod:`.routes.ui`."""

from typing import Dict, Callable, List
from urllib.parse import urlparse, urlunparse, urlencode, ParseResult

from flask import request, url_for


def url_for_page_builder() -> Dict[str, Callable]:
    """Add a page URL builder function to the template context."""

    def url_for_page(page: int, size: int) -> str:
        """Build an URL to for a search result page."""
        rule = request.url_rule
        parts = urlparse(url_for(rule.endpoint))  # type: ignore
        args = request.args.copy()
        args["start"] = (page - 1) * size
        parts = parts._replace(query=urlencode(list(args.items(multi=True))))
        url: str = urlunparse(parts)
        return url

    return {"url_for_page": url_for_page}


def current_url_params_builder() -> Dict[str, Callable]:
    """Add a function that gets the GET params from the current URL."""

    def current_url_params() -> str:
        """Get the GET params from the current URL."""
        params: str = urlencode(list(request.args.items(multi=True)))
        return params

    return {"current_url_params": current_url_params}


def current_url_sans_parameters_builder() -> Dict[str, Callable]:
    """Add a function to strip GET parameters from the current URL."""

    def current_url_sans_parameters(*params_to_remove: str) -> str:
        """Get the current URL with ``param`` removed from GET parameters."""
        if request.url_rule is None:
            raise ValueError("No matching URL rule for this request (oddly)")
        rule = request.url_rule
        parts = urlparse(url_for(rule.endpoint))
        args = request.args.copy()
        for param in params_to_remove:
            args.pop(param, None)
        parts = parts._replace(query=urlencode(list(args.items(multi=True))))
        url: str = urlunparse(parts)
        return url

    return {"current_url_sans_parameters": current_url_sans_parameters}


def url_for_author_search_builder() -> Dict[str, Callable]:
    """Inject a function to build author name query URLs."""
    search_url = urlparse(url_for("ui.search"))

    archives_urls: Dict[str, ParseResult] = {}

    def get_archives_url(archives: List[str]) -> ParseResult:
        key = ",".join(archives)
        if key not in archives_urls:
            archives_urls[key] = urlparse(
                url_for("ui.search", archives=archives)
            )
        return archives_urls[key]

    def url_for_author_search(forename: str, surname: str) -> str:
        # If we are in an archive-specific context, we want to preserve that
        # when generating URLs for author queries in search results.
        archives = request.view_args.get("archives")
        parts = get_archives_url(archives) if archives else search_url

        if forename:
            fparts = [part[0] for part in forename.split()]
            forename_part = " ".join(fparts)
            name = f"{surname}, {forename_part}"
        else:
            name = surname
        parts = parts._replace(
            query=urlencode({"searchtype": "author", "query": name})
        )
        url: str = urlunparse(parts)
        return url

    return {"url_for_author_search": url_for_author_search}


def url_with_params_builder() -> Dict[str, Callable]:
    """Inject a URL builder that handles GET parameters."""

    def url_with_params(name: str, values: dict, params: dict) -> str:
        """Build a URL for ``name`` with path ``values`` and GET ``params``."""
        parts = urlparse(url_for(name, **values))
        parts = parts._replace(query=urlencode(params))
        url: str = urlunparse(parts)
        return url

    return {"url_with_params": url_with_params}


def is_current_builder() -> Dict[str, Callable]:
    """Inject a function to evaluate whether or not a result is current."""

    def is_current(result: dict) -> bool:
        """Determine whether the result is the current version."""
        if result["submitted_date_all"] is None:
            return bool(result["is_current"])
        try:
            return bool(
                result["is_current"]
                and result["version"] == len(result["submitted_date_all"])
            )
        except Exception:
            return True
        return False

    return {"is_current": is_current}


context_processors: List[Callable[[], Dict[str, Callable]]] = [
    url_for_page_builder,
    current_url_params_builder,
    current_url_sans_parameters_builder,
    url_for_author_search_builder,
    url_with_params_builder,
    is_current_builder,
]
