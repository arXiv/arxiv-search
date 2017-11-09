from search.services import index, fulltext, metadata


def health() -> tuple:
    """Check integrations."""
    return {
        'fulltext': index.ok(),
        'index': index.ok(),
        'metadata': metadata.ok()
    }, 200, {}


def search(**query) -> tuple:
    """Handle search requests."""
    try:
        results = index.search(**query)
    except ValueError as e:    #
        results = None   # TODO: handle this
    except IOError as e:
        results = None   # TODO: handle this
    return {'results': results}, 200, {}
