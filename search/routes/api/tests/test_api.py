"""Tests for API routes."""

import os
import json
from http import HTTPStatus
from unittest import TestCase, mock, skip

import jsonschema

from search import factory
from search.tests import mocks
from search.domain.api import APIQuery, get_required_fields


class TestAPISearchRequests(TestCase):
    """Requests against the main search API."""

    SCHEMA_PATH = os.path.abspath("schema/resources/DocumentSet.json")

    def setUp(self):
        """Instantiate and configure an API app."""
        self.app = factory.create_api_web_app()
        self.client = self.app.test_client()

        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @mock.patch(f"{factory.__name__}.api.api")
    def test_with_valid_token(self, mock_controller):
        """Client auth token has required public read scope."""
        document = mocks.document()
        docs = {
            "results": [document],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }
        r_data = {"results": docs, "query": APIQuery()}
        mock_controller.search.return_value = r_data, HTTPStatus.OK, {}
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = json.loads(response.data)
        res = jsonschema.RefResolver(
            "file://%s/" % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None,
        )
        self.assertIsNone(
            jsonschema.validate(data, self.schema, resolver=res),
            "Response content is valid per schema",
        )

        for field in get_required_fields():
            self.assertIn(field, data["results"][0])

    @mock.patch(f"{factory.__name__}.api.api")
    def test_with_valid_token_limit_fields(self, mock_controller):
        """Client auth token has required public read scope."""
        document = mocks.document()
        docs = {
            "results": [document],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }

        query = APIQuery(include_fields=["abstract", "license"])
        r_data = {"results": docs, "query": query}
        mock_controller.search.return_value = r_data, HTTPStatus.OK, {}
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = json.loads(response.data)
        res = jsonschema.RefResolver(
            "file://%s/" % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None,
        )
        self.assertIsNone(
            jsonschema.validate(data, self.schema, resolver=res),
            "Response content is valid per schema",
        )

        # for field in domain.api.get_required_fields():
        self.assertEqual(
            set(data["results"][0].keys()), set(query.include_fields)
        )

    @mock.patch(f"{factory.__name__}.api.api")
    def test_paper_retrieval(self, mock_controller):
        """Test single-paper retrieval."""
        document = mocks.document()
        docs = {
            "results": [document],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }
        r_data = {"results": docs, "query": APIQuery()}
        mock_controller.paper.return_value = r_data, HTTPStatus.OK, {}
        response = self.client.get("/1234.56789v6")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = json.loads(response.data)
        res = jsonschema.RefResolver(
            "file://%s/" % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None,
        )
        self.assertIsNone(
            jsonschema.validate(data, self.schema, resolver=res),
            "Response content is valid per schema",
        )

        for field in get_required_fields():
            self.assertIn(field, data["results"][0])
