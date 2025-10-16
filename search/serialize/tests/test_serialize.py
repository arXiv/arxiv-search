"""Tests for serializers."""

import os
import json
from unittest import TestCase, mock
import pytest

import jsonschema

from search import encode
from search import serialize
from search.tests import mocks
from search.factory import create_api_web_app, create_classic_api_web_app


def mock_jsonify(o):
    return json.dumps(o, cls=encode.ISO8601JSONEncoder)


class TestSerializeJSONDocument(TestCase):
    """Serialize a single :class:`domain.Document` as JSON."""

    SCHEMA_PATH = os.path.abspath("schema/resources/Document.json")

    def setUp(self):
        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @mock.patch(
        f"search.serialize.json.url_for", lambda *a, **k: "http://f/12"
    )
    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    @mock.patch(f"search.serialize.json.jsonify", mock_jsonify)
    def test_to_json(self):
        """Just your run-of-the-mill arXiv document generates valid JSON."""
        app = create_api_web_app()
        with app.app_context():
            document = mocks.document()
            srlzd = serialize.as_json(document)
            res = jsonschema.RefResolver(
                "file://%s/"
                % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
                None,
            )
            self.assertIsNone(
                jsonschema.validate(
                    json.loads(srlzd), self.schema, resolver=res
                )
            )


class TestSerializeJSONDocumentSet(TestCase):
    """Serialize a :class:`domain.DocumentSet` as JSON."""

    SCHEMA_PATH = os.path.abspath("schema/resources/DocumentSet.json")

    def setUp(self):
        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @mock.patch(
        f"search.serialize.json.url_for", lambda *a, **k: "http://f/12"
    )
    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    @mock.patch(f"search.serialize.json.jsonify", mock_jsonify)
    def test_to_json(self):
        """Just your run-of-the-mill arXiv document generates valid JSON."""
        app = create_api_web_app()
        with app.app_context():
            document = mocks.document()
            meta = {"start": 0, "size": 50, "end": 50, "total": 500202}
            document_set = {"results": [document], "metadata": meta}
            srlzd = serialize.as_json(document_set)
            res = jsonschema.RefResolver(
                "file://%s/"
                % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
                None,
            )
            self.assertIsNone(
                jsonschema.validate(
                    json.loads(srlzd), self.schema, resolver=res
                )
            )


class TestSerializeAtomDocument(TestCase):
    """Serialize a single :class:`domain.Document` as Atom."""

    @mock.patch(
        f"search.serialize.atom.url_for", lambda *a, **k: "http://f/12"
    )
    def test_to_atom(self):
        """Just your run-of-the-mill arXiv document generates valid Atom."""
        app = create_classic_api_web_app()
        with app.app_context():
            document = mocks.document()
            _ = serialize.as_atom(document)

            # TODO: Verify valid AtomXML
