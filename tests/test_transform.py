"""Tests for :mod:`search.transform`."""

import unittest
import json
import jsonschema
from datetime import datetime, date
from search.process import transform
from search.domain import Document, DocMeta


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


class TestPublidationDates(unittest.TestCase):
    """:func:`.transform._constructPubDate` generates a list of datetimes."""

    def test_old_versions_are_available(self):
        """Publication dates from all versions are included."""
        meta = DocMeta({
            'paper_id': '1234.56789',
            'modtime': '2012-08-27T14:28:42-0400',
            'version': 3,
            'previous_versions': [
                DocMeta({
                    'version': 1,
                    'modtime': '2012-09-27T14:28:42-0400',
                }),
                DocMeta({
                    'version': 2,
                    'modtime': '2012-10-27T14:28:42-0400',
                })
            ]
        })
        pubdates = transform._constructPubDate(meta)

        self.assertIsInstance(pubdates, list)
        self.assertEqual(len(pubdates), 3)
        for pubdate in pubdates:
            self.assertIsInstance(pubdate, str)
            try:
                asdate = datetime.strptime(pubdate, '%Y%m%d').date()
            except ValueError:
                self.fail('Expected only year, month, and day: %s' % pubdate)

    def test_old_versions_not_available(self):
        """Only the current publication date is included."""
        meta = DocMeta({
            'paper_id': '1234.56789',
            'modtime': '2012-08-27T14:28:42-0400',
            'version': 3
        })
        pubdates = transform._constructPubDate(meta)
        self.assertEqual(len(pubdates), 1)
        asdate = datetime.strptime(pubdates[0], '%Y%m%d').date()
        self.assertEqual(asdate, date(year=2012, month=8, day=27))

    def test_old_versions_have_malformed_pubdate(self):
        """Versions with bad pubdates are excluded."""
        meta = DocMeta({
            'paper_id': '1234.56789',
            'modtime': '2012-08-27T14:28:42-0400',
            'version': 3,
            'previous_versions': [
                DocMeta({
                    'version': 1,
                    'modtime': '2000012-09-27T14:28:42-0400',
                }),
                DocMeta({
                    'version': 2,
                    'modtime': '2012-10-27T14:28:42-0400',
                })
            ]
        })
        pubdates = transform._constructPubDate(meta)
        self.assertEqual(len(pubdates), 2)
