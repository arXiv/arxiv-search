"""Tests for :mod:`search.transform`."""

from unittest import TestCase
import json
import jsonschema
from datetime import datetime, date
from search.process import transform
from search.domain import Document, DocMeta


class TestTransformMetdata(TestCase):
    """Test transformations for each of the metadata fields."""

    def test_id(self):
        """Field ``id`` is populated from ``paper_id``."""
        meta = DocMeta(**{'paper_id': '1234.56789'})
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.id, '1234.56789v1')

    def test_abstract(self):
        """Field ``abstract`` is populated from ``abstract_utf8``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'abstract_utf8': 'abstract!'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.abstract, 'abstract!')

    def test_authors(self):
        """Field ``authors`` is populated from ``authors_parsed``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'authors_parsed': [
                {
                    'first_name': 'B. Ivan',
                    'last_name': 'Dole'
                }
            ]
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.authors[0]['first_name'], 'B. Ivan')
        self.assertEqual(doc.authors[0]['last_name'], 'Dole')
        self.assertEqual(doc.authors[0]['full_name'], 'B. Ivan Dole',
                         "full_name should be generated from first_name and"
                         " last_name")
        self.assertEqual(doc.authors[0]['initials'], "B I",
                         "initials should be generated from first name")

    def test_authors_freeform(self):
        """Field ``authors_freeform`` is populated from ``authors_utf8``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'authors_utf8': 'authors!'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.authors_freeform, 'authors!')

    def test_owners(self):
        """Field ``owners`` is populated from ``author_owners``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'author_owners': [
                {
                    'first_name': 'B. Ivan',
                    'last_name': 'Dole'
                }
            ]
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.owners[0]['first_name'], 'B. Ivan')
        self.assertEqual(doc.owners[0]['last_name'], 'Dole')
        self.assertEqual(doc.owners[0]['full_name'], 'B. Ivan Dole',
                         "full_name should be generated from first_name and"
                         " last_name")
        self.assertEqual(doc.owners[0]['initials'], "B I",
                         "initials should be generated from first name")

    def test_submitted_date(self):
        """Field ``submitted_date`` is populated from ``submitted_date``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'submitted_date': '2007-04-25T16:06:50-0400'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.submitted_date, '2007-04-25T16:06:50-0400')

    def test_submitted_date_all(self):
        """``submitted_date_all`` is populated from ``submitted_date_all``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            "submitted_date_all": [
                "2007-04-25T15:58:28-0400", "2007-04-25T16:06:50-0400"
            ],
            'is_current': True
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.submitted_date_all[0], '2007-04-25T15:58:28-0400')
        self.assertEqual(doc.submitted_date_all[1], '2007-04-25T16:06:50-0400')
        self.assertEqual(doc.submitted_date_first, '2007-04-25T15:58:28-0400',
                         "Should be populated from submitted_date_all")
        self.assertEqual(doc.submitted_date_latest, "2007-04-25T16:06:50-0400",
                         "Should be populated from submitted_date_all")

    def test_modified_date(self):
        """Field ``modified_date`` is populated from ``modified_date``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'modified_date': '2007-04-25T16:06:50-0400'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.modified_date, '2007-04-25T16:06:50-0400')

    def test_updated_date(self):
        """Field ``updated_date`` is populated from ``updated_date``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'updated_date': '2007-04-25T16:06:50-0400'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.updated_date, '2007-04-25T16:06:50-0400')

    def test_announced_date_first(self):
        """``announced_date_first`` populated from ``announced_date_first``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'announced_date_first': '2007-04'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.announced_date_first, '2007-04')

    def test_is_withdrawn(self):
        """Field ``is_withdrawn`` is populated from ``is_withdrawn``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'is_withdrawn': False
        })
        doc = transform.to_search_document(meta)
        self.assertFalse(doc.is_withdrawn)

    def test_license(self):
        """Field ``license`` is populated from ``license``."""
        _license = {
            "label": "arXiv.org perpetual, non-exclusive license to"
                     " distribute this article",
            "uri": "http://arxiv.org/licenses/nonexclusive-distrib/1.0/"
        }
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'license': _license
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.license['uri'], _license['uri'])
        self.assertEqual(doc.license['label'], _license['label'])

        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'license': {'uri': None, 'label': None}
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.license['uri'], transform.DEFAULT_LICENSE['uri'],
                         "The default license should be used")
        self.assertEqual(doc.license['label'],
                         transform.DEFAULT_LICENSE['label'],
                         "The default license should be used")

    def test_paper_version(self):
        """Field ``paper_id_v`` is populated from ``paper_id``."""
        meta = DocMeta(**{'paper_id': '1234.56789', 'version': 4})
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.paper_id_v, '1234.56789v4')

    def test_primary_classification(self):
        """``primary_classification`` set from ``primary_classification``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'primary_classification': {
                "group": {
                    "name": "Physics",
                    "id": "physics"
                },
                "archive": {
                    "name": "Astrophysics",
                    "id": "astro-ph"
                },
                "category": {
                    "name": "Astrophysics",
                    "id": "astro-ph"
                }
            }
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.primary_classification,
                         meta.primary_classification)

    def test_secondary_classification(self):
        """``secondary_classification`` from ``secondary_classification``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'secondary_classification': [{
                "group": {
                    "name": "Physics",
                    "id": "physics"
                },
                "archive": {
                    "name": "Astrophysics",
                    "id": "astro-ph"
                },
                "category": {
                    "name": "Astrophysics",
                    "id": "astro-ph"
                }
            }]
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.secondary_classification,
                         meta.secondary_classification)

    def test_title(self):
        """Field ``title`` is populated from ``title_utf8``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'title_utf8': 'foo title'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.title, 'foo title')

    def test_title_utf8(self):
        """Field ``title`` is populated from ``title_utf8``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'title_utf8': 'foö title'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.title, 'foö title')

    def test_source(self):
        """Field ``source`` is populated from ``source``."""
        _source = {"flags": "1", "format": "pdf", "size_bytes": 1230119}
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'source': _source
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.source, _source)

    def test_version(self):
        """Field ``version`` is populated from ``version``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'version': 25
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.version, 25)

    def test_submitter(self):
        """Field ``submitter`` is populated from ``submitter``."""
        _submitter = {
            "email": "s.mitter@cornell.edu",
            "name": "Sub Mitter",
            "name_utf8": "Süb Mitter"
        }
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'submitter': _submitter
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.submitter, _submitter)

    def test_report_num(self):
        """Field ``report_num`` is populated from ``report_num``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'report_num': "Physica A, 245 (1997) 181"
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.report_num, "Physica A, 245 (1997) 181")

    def test_proxy(self):
        """Field ``proxy`` is populated from ``proxy``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'proxy': True
        })
        doc = transform.to_search_document(meta)
        self.assertTrue(doc.proxy)

    def test_metadata_id(self):
        """Field ``metadata_id`` is populated from ``metadata_id``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'metadata_id': '690776'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.metadata_id, '690776')

    def test_msc_class(self):
        """Field ``msc_class`` is populated from ``msc_class``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'msc_class': "03B70,68Q60"
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.msc_class, ["03B70", "68Q60"])

    def test_acm_class(self):
        """Field ``acm_class`` is populated from ``acm_class``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'acm_class': "F.4.1; D.2.4"
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.acm_class, ["F.4.1", "D.2.4"])

    def test_metadata_id(self):
        """Field ``doi`` is populated from ``doi``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'doi': '10.1103/PhysRevD.76.104043'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.doi, '10.1103/PhysRevD.76.104043')

    def test_metadata_id(self):
        """Field ``comments`` is populated from ``comments_utf8``."""
        meta = DocMeta(**{
            'paper_id': '1234.56789',
            'comments_utf8': 'comments!'
        })
        doc = transform.to_search_document(meta)
        self.assertEqual(doc.comments, 'comments!')


class TestTransformBulkDocmeta(TestCase):
    """Test transformation of docmeta retrieved from bulk endpoint."""

    def test_transform(self):
        """All of the paper ID and version fields should be set correctly."""
        with open('tests/data/docmeta_bulk.json') as f:
            data = json.load(f)

        docmeta = [DocMeta(**datum) for datum in data]

        documents = [transform.to_search_document(meta) for meta in docmeta]
        for doc in documents:
            self.assertIsNotNone(doc.id)
            self.assertGreater(len(doc.id), 0)
            self.assertIsNotNone(doc.paper_id)
            self.assertGreater(len(doc.paper_id), 0)
            self.assertNotIn('v', doc.paper_id)
            self.assertIsNotNone(doc.paper_id_v)
            self.assertGreater(len(doc.paper_id_v), 0)
            self.assertIn('v', doc.paper_id_v)
            self.assertIsNotNone(doc.version)
            self.assertGreater(doc.version, 0)

            if doc.version == 2:
                self.assertEqual(doc.latest, f"{doc.paper_id}v2")
                self.assertTrue(doc.is_current)
                self.assertEqual(doc.id, doc.paper_id_v)
            else:
                self.assertFalse(doc.is_current)
                self.assertEqual(doc.id, doc.paper_id_v)
            self.assertEqual(doc.latest_version, 2)
