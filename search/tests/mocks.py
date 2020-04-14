"""Provide function to return a mock document."""
from datetime import datetime


def document():
    """Return a mock document."""
    return {
        "submitted_date": datetime.now(),
        "submitted_date_first": datetime.now(),
        "announced_date_first": datetime.now(),
        "id": "1234.5678",
        "abstract": "very abstract",
        "authors": [{"full_name": "F. Bar", "orcid": "1234-5678-9012-3456"}],
        "submitter": {"full_name": "S. Ubmitter", "author_id": "su_1"},
        "modified_date": datetime.now(),
        "updated_date": datetime.now(),
        "is_current": True,
        "is_withdrawn": False,
        "license": {"uri": "http://foo.license/1", "label": "Notalicense 5.4"},
        "paper_id": "1234.5678",
        "paper_id_v": "1234.5678v6",
        "title": "tiiiitle",
        "source": {"flags": "A", "format": "pdftotex", "size_bytes": 2},
        "version": 6,
        "latest": "1234.5678v6",
        "latest_version": 6,
        "report_num": "somenum1",
        "msc_class": ["c1"],
        "acm_class": ["z2"],
        "journal_ref": "somejournal (1991): 2-34",
        "doi": "10.123456/7890",
        "comments": "very science",
        "abs_categories": "astro-ph.CO foo.BR",
        "formats": ["pdf", "other"],
        "primary_classification": {
            "group": {"id": "foo", "name": "Foo Group"},
            "archive": {"id": "foo", "name": "Foo Archive"},
            "category": {"id": "foo.BR", "name": "Foo Category"},
        },
        "secondary_classification": [
            {
                "group": {"id": "foo", "name": "Foo Group"},
                "archive": {"id": "foo", "name": "Foo Archive"},
                "category": {"id": "foo.BZ", "name": "Baz Category"},
            }
        ],
    }
