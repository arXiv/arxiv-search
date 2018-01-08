"""Tests for :mod:`search.transform`."""

import unittest
import json
import jsonschema
from search.process import transform
from search.domain import Document


class TestMetadataAreAvailable(unittest.TestCase):
    """Only metadata are available for a document."""

    def setUp(self):
        """Load document schema and sample metadata."""
        with open('schema/Document.json') as f:
            self.schema = json.load(f)
        with open('tests/data/1106.1238v2.json') as f:
            self.metadata = json.load(f)

    def test_returns_valid_document(self):
        """:func:`.transform.to_search_document` returns a valid document."""
        document = transform.to_search_document(self.metadata)
        try:
            jsonschema.validate(document, self.schema)
        except jsonschema.ValidationError as e:
            self.fail('Not a valid document: %s' % e)
        self.assertIsInstance(document, Document)
        self.assertTrue(document.valid)

    def test_fulltext_not_included(self):
        """The key ``fulltext`` is excluded from the document."""
        document = transform.to_search_document(self.metadata)
        self.assertFalse('fulltext' in document)
        self.assertIsInstance(document, Document)
        self.assertTrue(document.valid)


class TestFulltextAvailable(unittest.TestCase):
    """Fulltext content is available for a document."""

    def setUp(self):
        """Load document schema, fulltext, and sample metadata."""
        with open('schema/Document.json') as f:
            self.schema = json.load(f)
        with open('tests/data/1106.1238v2.json') as f:
            self.metadata = json.load(f)
        with open('tests/data/fulltext.json') as f:
            self.fulltext = json.load(f)

    def test_returns_valid_document(self):
        """:func:`.transform.to_search_document` returns a valid document."""
        document = transform.to_search_document(self.metadata, self.fulltext)
        try:
            jsonschema.validate(document, self.schema)
        except jsonschema.ValidationError as e:
            self.fail('Not a valid document: %s' % e)
        self.assertIsInstance(document, Document)
        self.assertTrue(document.valid)

    def test_fulltext_is_included(self):
        """The key ``fulltext`` is included in the document."""
        document = transform.to_search_document(self.metadata, self.fulltext)
        self.assertTrue('fulltext' in document)
        self.assertIsInstance(document['fulltext'], str)
        self.assertIsInstance(document, Document)
        self.assertTrue(document.valid)


class TestPaperVersion(unittest.TestCase):
    """A value for ``paper_id_v`` is required."""

    def test_paper_id_has_version(self):
        """Return ``paper_id`` if version is already included."""
        meta = {'paper_id': '1234.5678v5', 'version': 5}
        self.assertEqual(transform._constructPaperVersion(meta),
                         meta['paper_id'])

    def test_paper_id_has_no_version(self):
        """Articulate ``paper_id`` from id and version."""
        meta = {'paper_id': '1234.5678', 'version': 5}
        self.assertEqual(transform._constructPaperVersion(meta),
                         '1234.5678v5')

    def test_version_not_included(self):
        """Treat as version 1."""
        meta = {'paper_id': '1234.5678'}
        self.assertEqual(transform._constructPaperVersion(meta),
                         '1234.5678v1')
