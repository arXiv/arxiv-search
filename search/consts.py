from pytz import timezone

# Sorting

DEFAULT_SORT_ORDER = [
    {"announced_date_first": {"order": "desc"}},
    {"_doc": {"order": "asc"}},
]


# Timezones

EASTERN = timezone("US/Eastern")
