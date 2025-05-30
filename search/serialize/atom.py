"""Atom serialization for classic arXiv API."""

import base64
import hashlib
from urllib import parse
from datetime import datetime
from typing import Union, Optional, Dict, Any

from flask import url_for
from feedgen.feed import FeedGenerator

from search.utils import to_utc, safe_str
from search.domain import (
    Error,
    DocumentSet,
    Document,
    ClassicAPIQuery,
    document_set_from_documents,
)
from search.serialize.atom_extensions import (
    ArXivExtension,
    ArXivEntryExtension,
    OpenSearchExtension,
    ARXIV_NS,
)
from search.domain.classic_api.query_parser import phrase_to_query_string
from search.serialize.base import BaseSerializer


class AtomXMLSerializer(BaseSerializer):
    """Atom XML serializer for paper metadata."""

    @staticmethod
    def _fix_id_url(url: str) -> str:
        return (
            parse.urlparse(url)
            ._replace(scheme="http")
            ._replace(netloc="arxiv.org")
            .geturl()
        )

    @staticmethod
    def _fix_url(url: str) -> str:
        return (
            parse.urlparse(url)
            ._replace(scheme="https")
            ._replace(netloc="arxiv.org")
            .geturl()
        )

    def transform_document(
        self,
        fg: FeedGenerator,
        doc: Document,
        query: Optional[ClassicAPIQuery] = None,
    ) -> None:
        """Select a subset of :class:`Document` properties for public API."""
        entry = fg.add_entry()
        entry.id(
            self._fix_id_url(
                url_for(
                    "abs",
                    paper_id=doc["paper_id"],
                    version=doc["version"],
                    _external=True,
                )
            )
        )
        entry.title(doc["title"])
        entry.summary(doc["abstract"])
        entry.published(
            to_utc(doc["submitted_date_first"] or doc["submitted_date"])
        )
        entry.updated(
            to_utc(
                doc["updated_date"]
                or doc["modified_date"]
                or doc["submitted_date"]
            )
        )
        entry.link(
            {
                "href": self._fix_url(
                    url_for(
                        "abs",
                        paper_id=doc["paper_id"],
                        version=doc["version"],
                        _external=True,
                    )
                ),
                "type": "text/html",
            }
        )

        entry.link(
            {
                "href": self._fix_url(
                    url_for(
                        "pdf",
                        paper_id=doc["paper_id"],
                        version=doc["version"],
                        _external=True,
                    )
                ),
                "type": "application/pdf",
                "rel": "related",
                "title": "pdf",
            }
        )

        if doc.get("comments"):
            entry.arxiv.comment(doc["comments"])

        if doc.get("journal_ref"):
            entry.arxiv.journal_ref(doc["journal_ref"])

        if doc.get("doi"):
            entry.arxiv.doi(doc["doi"])

        if doc["primary_classification"]["category"] is not None:
            entry.arxiv.primary_category(
                doc["primary_classification"]["category"]["id"]
            )
            entry.category(
                term=doc["primary_classification"]["category"]["id"],
                scheme=ARXIV_NS,
            )

        for category in doc["secondary_classification"]:
            entry.category(term=category["category"]["id"], scheme=ARXIV_NS)

        for author in doc["authors"]:
            author_data: Dict[str, Any] = {"name": author["full_name"]}
            if author.get("affiliation"):
                author_data["affiliation"] = author["affiliation"]
            entry.arxiv.author(author_data)

    @classmethod
    def _get_feed(
        cls, query: Optional[ClassicAPIQuery] = None
    ) -> FeedGenerator:
        fg = FeedGenerator()
        fg.generator("")
        fg.register_extension("opensearch", OpenSearchExtension)
        fg.register_extension(
            "arxiv", ArXivExtension, ArXivEntryExtension, rss=False
        )

        if query:
            if query.phrase is not None:
                query_string = phrase_to_query_string(query.phrase)
            else:
                query_string = ""

            if query.id_list:
                id_list = ",".join(query.id_list)
            else:
                id_list = ""

            fg.title(f"arXiv Query: {query.to_query_string()}")

            # From perl documentation of the old site:
            # search_id is calculated by taking SHA-1 digest of the query
            # string. Digest is in bytes form and it's 20 bytes long. Then it's
            # base64 encoded, but perls version returns only 27 characters -
            # it omits the `=` sign at the end.
            search_id = base64.b64encode(
                hashlib.sha1(query.to_query_string().encode("utf-8")).digest()
            ).decode("utf-8")[:-1]
            fg.id(
                cls._fix_url(
                    url_for("classic_api.query").replace(
                        "/query", f"/{search_id}"
                    )
                )
            )

            fg.link(
                {
                    "href": cls._fix_url(
                        url_for(
                            "classic_api.query",
                            search_query=query_string,
                            start=query.page_start,
                            max_results=query.size,
                            id_list=id_list,
                        )
                    ),
                    "type": "application/atom+xml",
                }
            )
        else:
            # TODO: Discuss better defaults
            fg.title("arXiv Search Results")
            fg.id("https://arxiv.org/")

        fg.updated(to_utc(datetime.utcnow()))
        return fg

    def serialize(
        self,
        document_set: DocumentSet,
        query: Optional[ClassicAPIQuery] = None,
    ) -> str:
        """Generate Atom response for a :class:`DocumentSet`."""
        fg = self._get_feed(query)

        # pylint struggles with the opensearch extensions, so we ignore
        # no-member here.
        # pylint: disable=no-member
        fg.opensearch.totalResults(
            document_set["metadata"].get("total_results")
        )
        fg.opensearch.itemsPerPage(document_set["metadata"].get("size"))
        fg.opensearch.startIndex(document_set["metadata"].get("start"))

        for doc in reversed(document_set["results"]):
            self.transform_document(fg, doc, query=query)

        return safe_str(fg.atom_str(pretty=True))  # type: ignore

    def serialize_error(
        self, error: Error, query: Optional[ClassicAPIQuery] = None
    ) -> str:
        """Generate Atom error response."""
        fg = self._get_feed(query)

        # pylint struggles with the opensearch extensions, so we ignore
        # no-member here.
        # pylint: disable=no-member
        fg.opensearch.totalResults(1)
        fg.opensearch.itemsPerPage(1)
        fg.opensearch.startIndex(0)

        entry = fg.add_entry()
        entry.id(error.id)
        entry.title("Error")
        entry.summary(error.error)
        entry.updated(to_utc(error.created))
        entry.link(
            {
                "href": self._fix_url(error.link),
                "rel": "alternate",
                "type": "text/html",
            }
        )
        entry.arxiv.author({"name": error.author})

        return safe_str(fg.atom_str(pretty=True))  # type: ignore

    def serialize_document(
        self, document: Document, query: Optional[ClassicAPIQuery] = None
    ) -> str:
        """Generate Atom feed for a single :class:`Document`."""
        # Wrap the single document in a DocumentSet wrapper.
        document_set = document_set_from_documents([document])

        return self.serialize(document_set, query=query)


def as_atom(
    document_or_set: Union[Error, DocumentSet, Document],
    query: Optional[ClassicAPIQuery] = None,
) -> str:
    """Serialize a :class:`DocumentSet` as Atom."""
    if isinstance(document_or_set, Error):
        return AtomXMLSerializer().serialize_error(
            document_or_set, query=query
        )  # type: ignore
        # type: ignore
    elif "paper_id" in document_or_set:
        return AtomXMLSerializer().serialize_document(  # type: ignore
            document_or_set, query=query
        )
    return AtomXMLSerializer().serialize(  # type: ignore
        document_or_set, query=query
    )  # type: ignore
