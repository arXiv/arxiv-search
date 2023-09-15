"""Tests for serializers."""

import os
from unittest import TestCase, mock
from datetime import datetime
import json
import jsonschema
from .... import domain, encode
from .. import serialize


def mock_jsonify(o):
    return json.dumps(o, cls=encode.ISO8601JSONEncoder)


class TestSerializeJSONDocument(TestCase):
    """Serialize a single :class:`domain.Document` as JSON."""

    SCHEMA_PATH = os.path.abspath('schema/resources/Document.json')

    def setUp(self):
        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @mock.patch(f'{serialize.__name__}.url_for', lambda *a, **k: 'http://f/12')
    @mock.patch(f'{serialize.__name__}.jsonify', mock_jsonify)
    def test_to_json(self):
        """Just your run-of-the-mill arXiv document generates valid JSON."""
        document = domain.Document(
            submitted_date=datetime.now(),
            submitted_date_first=datetime.now(),
            announced_date_first=datetime.now(),
            id='1234.5678',
            abstract='very abstract',
            authors=[
                domain.Person(full_name='F. Bar', orcid='1234-5678-9012-3456')
            ],
            submitter=domain.Person(full_name='S. Ubmitter', author_id='su_1'),
            modified_date=datetime.now(),
            updated_date=datetime.now(),
            is_current=True,
            is_withdrawn=False,
            license={
                'uri': 'http://foo.license/1',
                'label': 'Notalicense 5.4'
            },
            paper_id='1234.5678',
            paper_id_v='1234.5678v6',
            title='tiiiitle',
            source={
                'flags': 'A',
                'format': 'pdftotex',
                'size_bytes': 2
            },
            version=6,
            latest='1234.5678v6',
            latest_version=6,
            report_num='somenum1',
            msc_class=['c1'],
            acm_class=['z2'],
            journal_ref='somejournal (1991): 2-34',
            doi='10.123456/7890',
            comments='very science',
            abs_categories='astro-ph.CO foo.BR',
            formats=['pdf', 'other'],
            primary_classification=domain.Classification(
                group={'id': 'foo', 'name': 'Foo Group'},
                archive={'id': 'foo', 'name': 'Foo Archive'},
                category={'id': 'foo.BR', 'name': 'Foo Category'},
            ),
            secondary_classification=[
                domain.Classification(
                    group={'id': 'foo', 'name': 'Foo Group'},
                    archive={'id': 'foo', 'name': 'Foo Archive'},
                    category={'id': 'foo.BZ', 'name': 'Baz Category'},
                )
            ]
        )
        srlzd = serialize.as_json(document)
        res = jsonschema.RefResolver(
            'file://%s/' % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None
        )
        self.assertIsNone(
            jsonschema.validate(json.loads(srlzd), self.schema, resolver=res)
        )


class TestSerializeJSONDocumentSet(TestCase):
    """Serialize a :class:`domain.DocumentSet` as JSON."""

    SCHEMA_PATH = os.path.abspath('schema/resources/DocumentSet.json')

    def setUp(self):
        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @mock.patch(f'{serialize.__name__}.url_for', lambda *a, **k: 'http://f/12')
    @mock.patch(f'{serialize.__name__}.jsonify', mock_jsonify)
    def test_to_json(self):
        """Just your run-of-the-mill arXiv document generates valid JSON."""
        document = domain.Document(
            submitted_date=datetime.now(),
            submitted_date_first=datetime.now(),
            announced_date_first=datetime.now(),
            id='1234.5678',
            abstract='very abstract',
            authors=[
                domain.Person(full_name='F. Bar', orcid='1234-5678-9012-3456')
            ],
            submitter=domain.Person(full_name='S. Ubmitter', author_id='su_1'),
            modified_date=datetime.now(),
            updated_date=datetime.now(),
            is_current=True,
            is_withdrawn=False,
            license={
                'uri': 'http://foo.license/1',
                'label': 'Notalicense 5.4'
            },
            paper_id='1234.5678',
            paper_id_v='1234.5678v6',
            title='tiiiitle',
            source={
                'flags': 'A',
                'format': 'pdftotex',
                'size_bytes': 2
            },
            version=6,
            latest='1234.5678v6',
            latest_version=6,
            report_num='somenum1',
            msc_class=['c1'],
            acm_class=['z2'],
            journal_ref='somejournal (1991): 2-34',
            doi='10.123456/7890',
            comments='very science',
            abs_categories='astro-ph.CO foo.BR',
            formats=['pdf', 'other'],
            primary_classification=domain.Classification(
                group={'id': 'foo', 'name': 'Foo Group'},
                archive={'id': 'foo', 'name': 'Foo Archive'},
                category={'id': 'foo.BR', 'name': 'Foo Category'},
            ),
            secondary_classification=[
                domain.Classification(
                    group={'id': 'foo', 'name': 'Foo Group'},
                    archive={'id': 'foo', 'name': 'Foo Archive'},
                    category={'id': 'foo.BZ', 'name': 'Baz Category'},
                )
            ]
        )
        meta = {'start': 0, 'size': 50, 'end': 50, 'total': 500202}
        document_set = domain.DocumentSet(results=[document], metadata=meta)
        srlzd = serialize.as_json(document_set)
        res = jsonschema.RefResolver(
            'file://%s/' % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None
        )
        self.assertIsNone(
            jsonschema.validate(json.loads(srlzd), self.schema, resolver=res)
        )
