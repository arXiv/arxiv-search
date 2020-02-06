"""Serializers for API responses."""

from typing import Union, Optional, Dict, Any
from flask import jsonify, url_for, Response

from search.serialize.base import BaseSerializer
from search.domain import DocumentSet, Document, Classification, APIQuery


class JSONSerializer(BaseSerializer):
    """Serializes a :class:`DocumentSet` as JSON."""

    # FIXME: Return type.
    @classmethod
    def _transform_classification(
        cls, clsn: Classification
    ) -> Optional[Dict[Any, Any]]:
        category = clsn.get("category")
        if category is None:
            return None
        return {
            "group": clsn.get("group"),
            "archive": clsn.get("archive"),
            "category": category,
        }

    # FIXME: Return type.
    @classmethod
    def _transform_format(
        cls, fmt: str, paper_id: str, version: int
    ) -> Dict[Any, Any]:
        return {
            "format": fmt,
            "href": url_for(fmt, paper_id=paper_id, version=version),
        }

    # FIXME: Return type.
    @classmethod
    def _transform_latest(cls, document: Document) -> Optional[Dict[Any, Any]]:
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

    # FIXME: Types.
    @classmethod
    def _transform_license(
        cls, license: Dict[Any, Any]
    ) -> Optional[Dict[Any, Any]]:
        uri = license.get("uri")
        if uri is None:
            return None
        return {"label": license.get("label", ""), "href": uri}

    # FIXME: Return type.
    @classmethod
    def transform_document(
        cls, doc: Document, query: Optional[APIQuery] = None
    ) -> Dict[Any, Any]:
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
                cls._transform_format(fmt, paper_id, version)
                for fmt in doc["formats"]
            ]
        if "license" in data:
            data["license"] = cls._transform_license(doc["license"])
        if "latest" in data:
            data["latest"] = cls._transform_latest(doc)

        data["href"] = url_for(
            "api.paper", paper_id=paper_id, version=version, _external=True
        )
        data["canonical"] = url_for("abs", paper_id=paper_id, version=version)
        return data

    @classmethod
    def serialize(
        cls, document_set: DocumentSet, query: Optional[APIQuery] = None
    ) -> Response:
        """Generate JSON for a :class:`DocumentSet`."""
        total_results = int(document_set["metadata"].get("total_results", 0))
        serialized: Response = jsonify(
            {
                "results": [
                    cls.transform_document(doc, query=query)
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

    @classmethod
    def serialize_document(
        cls, document: Document, query: Optional[APIQuery] = None
    ) -> Response:
        """Generate JSON for a single :class:`Document`."""
        serialized: Response = jsonify(
            cls.transform_document(document, query=query)
        )
        return serialized


def as_json(
    document_or_set: Union[DocumentSet, Document],
    query: Optional[APIQuery] = None,
) -> Response:
    """Serialize a :class:`DocumentSet` as JSON."""
    if "paper_id" in document_or_set:
        return JSONSerializer.serialize_document(
            document_or_set, query=query
        )  # type: ignore
    return JSONSerializer.serialize(
        document_or_set, query=query
    )  # type: ignore
