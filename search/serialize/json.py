"""Serializers for API responses."""

from typing import Union, Optional, Dict, Any
from flask import jsonify, url_for, Response

from search.serialize.base import BaseSerializer
from search.domain import DocumentSet, Document, Classification, APIQuery


class JSONSerializer(BaseSerializer):
    """Serializes a :class:`DocumentSet` as JSON."""

    @staticmethod
    def _transform_classification(
        clsn: Classification,
    ) -> Optional[Dict[str, Optional[str]]]:
        category = clsn.get("category")
        if category is None:
            return None
        return {
            "group": clsn.get("group"),
            "archive": clsn.get("archive"),
            "category": category,
        }

    @staticmethod
    def _transform_format(
        fmt: str, paper_id: str, version: int
    ) -> Dict[str, str]:
        return {
            "format": fmt,
            "href": url_for(fmt, paper_id=paper_id, version=version),
        }

    @staticmethod
    def _transform_latest(document: Document) -> Optional[Dict[str, str]]:
        latest = document.get("latest")
        if latest is None:
            return None
        return {
            "paper_id": latest,
            "href": url_for(
                "api.paper",
                paper_id=document["paper_id"],
                version=document.get("latest_version"),
                _external=True,
            ),
            "canonical": url_for(
                "abs",
                paper_id=document["paper_id"],
                version=document.get("latest_version"),
            ),
            "version": document.get("latest_version"),
        }

    @staticmethod
    def _transform_license(
        license: Dict[str, str]
    ) -> Optional[Dict[Any, Any]]:
        uri = license.get("uri")
        if uri is None:
            return None
        return {"label": license.get("label", ""), "href": uri}

    def transform_document(
        self, doc: Document, query: Optional[APIQuery] = None
    ) -> Dict[str, Any]:
        """Select a subset of :class:`Document` properties for public API."""
        # Only return fields that have been explicitly requested.
        data = {
            key: value
            for key, value in doc.items()
            if query is None or key in query.include_fields
        }
        paper_id = doc["paper_id"]
        version = doc["version"]
        if "submitted_date_first" in data:
            data["submitted_date_first"] = doc[
                "submitted_date_first"
            ].isoformat()
        if "announced_date_first" in data:
            data["announced_date_first"] = doc[
                "announced_date_first"
            ].isoformat()
        if "formats" in data:
            data["formats"] = [
                self._transform_format(fmt, paper_id, version)
                for fmt in doc["formats"]
            ]
        if "license" in data:
            data["license"] = self._transform_license(doc["license"])
        if "latest" in data:
            data["latest"] = self._transform_latest(doc)

        data["href"] = url_for(
            "api.paper", paper_id=paper_id, version=version, _external=True
        )
        data["canonical"] = url_for("abs", paper_id=paper_id, version=version)
        return data

    def serialize(
        self, document_set: DocumentSet, query: Optional[APIQuery] = None
    ) -> Response:
        """Generate JSON for a :class:`DocumentSet`."""
        total_results = int(document_set["metadata"].get("total_results", 0))
        serialized: Response = jsonify(
            {
                "results": [
                    self.transform_document(doc, query=query)
                    for doc in document_set["results"]
                ],
                "metadata": {
                    "start": document_set["metadata"].get("start", ""),
                    "end": document_set["metadata"].get("end", ""),
                    "size": document_set["metadata"].get("size", ""),
                    "total_results": total_results,
                    "query": document_set["metadata"].get("query", []),
                },
            }
        )
        return serialized

    def serialize_document(
        self, document: Document, query: Optional[APIQuery] = None,
    ) -> Response:
        """Generate JSON for a single :class:`Document`."""
        serialized: Response = jsonify(
            self.transform_document(document, query=query)
        )
        return serialized


def as_json(
    document_or_set: Union[DocumentSet, Document],
    query: Optional[APIQuery] = None,
) -> Response:
    """Serialize a :class:`DocumentSet` as JSON."""
    if "paper_id" in document_or_set:
        return JSONSerializer().serialize_document(  # type:ignore
            document_or_set, query=query
        )  # type: ignore
    return JSONSerializer().serialize(  # type:ignore
        document_or_set, query=query
    )
