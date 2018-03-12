"""
Integration and search behavior tests.

These tests evaluate the behavior of :mod:`.index` against a live Elasticsearch
cluster.
"""

from unittest import TestCase
import os
import subprocess
import time
from datetime import datetime
from pytz import timezone

from search.services import index
from search.agent.consumer import MetadataRecordProcessor
from search.domain import SimpleQuery, AuthorQuery, AuthorList, Author, \
    AdvancedQuery, DateRange, FieldedSearchList, FieldedSearchTerm

EASTERN = timezone('US/Eastern')


class TestSearchIntegration(TestCase):
    """Indexes a limited set of documents, and tests search behavior."""

    @classmethod
    def setUpClass(cls):
        """Spin up ES and index documents."""
        build_es = subprocess.run(
            "docker build ./"
            " -t arxiv/elasticsearch"
            " -f ./Dockerfile-elasticsearch",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        start_es = subprocess.run(
            "docker run -d -p 9201:9200 arxiv/elasticsearch",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        cls.es_container = start_es.stdout.decode('ascii').strip()
        os.environ['ELASTICSEARCH_SERVICE_HOST'] = 'localhost'
        os.environ['ELASTICSEARCH_SERVICE_PORT'] = "9201"
        os.environ['ELASTICSEARCH_PORT_9201_PROTO'] = "http"
        os.environ['ELASTICSEARCH_VERIFY'] = 'false'

        # Build and start the docmeta stub.
        build_docmeta = subprocess.run(
            "docker build ./"
            " -t arxiv/search-metadata"
            " -f ./Dockerfile-metadata",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        start_docmeta = subprocess.run(
            "docker run -d -p 9000:8000 arxiv/search-metadata",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        cls.md_container = start_docmeta.stdout.decode('ascii').strip()
        os.environ['METADATA_ENDPOINT'] = 'http://localhost:9000/docmeta/'

        print('Waiting for ES cluster to be available...')
        time.sleep(12)
        while True:
            time.sleep(5)
            if index.cluster_available():
                time.sleep(2)
                index.create_index()
                break

        to_index = [
            "1712.04442",    # flux capacitor
            "1511.07473",    # flux capacitor
            "1604.04228",    # flux capacitor
            "1403.6219",     # λ
            "1404.3450",     # $z_1$
            "1703.09067",    # $\lambda$
            "1408.6682",     # $\lambda$
            "1607.05107",    # Schröder
            "1509.08727",    # Schroder
            "1710.01597",    # Schroeder
            "1708.07156",    # w w
            "1401.1012",     # Wonmin Son
        ]
        # cls.cache_dir = os.path.abspath('tests/data/examples')
        cls.processor = MetadataRecordProcessor()
        # cls.processor.init_cache(cls.cache_dir)
        cls.processor.index_papers(to_index)
        time.sleep(5)    # Give a few seconds for docs to be available.

    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch once all tests have run."""
        stop_es = subprocess.run(f"docker rm -f {cls.es_container}",
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
        stop_md = subprocess.run(f"docker rm -f {cls.md_container}",
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)

    def test_simple_search_all_fields(self):
        """Scenario: simple term search across all fields."""
        # Given search term is "flux capacitor"
        # And selected field to search is "All fields"
        # When a user performs a search...
        query = SimpleQuery(
            order='',
            page_size=10,
            field='all',
            value='flux capacitor'
        )
        document_set = index.search(query)
        # All entries contain a metadata field that contains either "flux"
        # or "capacitor".
        self.assertEqual(len(document_set.results), 3)
        for item in document_set.results:
            self.assertTrue("flux" in str(item) or "capacitor" in str(item),
                            "Should have a metadata field that contains either"
                            " 'flux' or 'capacitor'.")


    def test_simple_search_for_utf8(self):
        """Scenario: simple search for utf8 terms."""

        # A search for a TeX expression should match similar metadata strings.
        query = SimpleQuery(
            order='',
            page_size=10,
            field='all',
            value='λ'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 1)
        self.assertEqual(document_set.results[0].id, "1403.6219")

    def test_simple_search_for_texism(self):
        """Scenario: simple search for TeX terms."""
        query = SimpleQuery(
            order='',
            page_size=10,
            field='all',
            value='$z_1$'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 1)
        self.assertEqual(document_set.results[0].id, "1404.3450")

    def test_simple_search_for_texism2(self):
        """Scenario: simple search for TeX terms."""
        query = SimpleQuery(
            order='',
            page_size=10,
            field='all',
            value='$\lambda$'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 2)

    def test_author_search_with_folding(self):
        """Scenario: searching for a surname."""
        query = AuthorQuery(
            order='',
            page_size=10,
            authors=AuthorList([Author(surname="schröder")])
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 2)
        self.assertIn("1607.05107", [r.id for r in document_set.results],
                      "Schröder should match.")
        self.assertIn("1509.08727", [r.id for r in document_set.results],
                      "Schroder should match.")

    def test_author_search_with_forename(self):
        """Scenario: searching with surname and forename."""
        query = AuthorQuery(
            order='',
            page_size=10,
            authors=AuthorList([Author(surname="w", forename="w")])
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 1)
        _ids = [r.id for r in document_set.results]
        self.assertIn("1708.07156", _ids, "Wissink B. W should match")
        self.assertNotIn("1401.1012", _ids, "Wonmin Son should not match.")

    def test_advanced_date_range_search(self):
        """Scenario: date range search."""
        search_year = 2015
        query = AdvancedQuery(
            order='',
            page_size=10,
            date_range=DateRange(
                start_date=datetime(year=2015, month=1, day=1, tzinfo=EASTERN),
                end_date=datetime(year=2016, month=1, day=1, tzinfo=EASTERN)
            )
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 3,
                         "Should be three results from 2015.")
        _ids = [r.paper_id_v for r in document_set.results]
        self.assertIn("1509.08727v1", _ids,
                      "Results should include older versions of papers.")
        self.assertIn("1408.6682v2", _ids)
        self.assertIn("1511.07473v1", _ids)

    def test_advanced_multiple_search_terms(self):
        """Scenario: multiple terms search success."""
        query = AdvancedQuery(
            order='',
            page_size=10,
            terms=FieldedSearchList([
                FieldedSearchTerm(operator='AND', field='author',
                                  term='schroder'),
                FieldedSearchTerm(operator='OR', field='title',
                                  term='jqk'),
            ])
        )
        document_set = index.search(query)
        _ids = [r.id for r in document_set.results]
        self.assertEqual(len(document_set.results), 2)
        self.assertIn("1607.05107", _ids, "Schröder should match.")
        self.assertIn("1509.08727", _ids, "Schroder should match.")

    def test_advanced_multiple_search_terms_fails(self):
        """Scenario: multiple terms with no results."""
        query = AdvancedQuery(
            order='',
            page_size=10,
            terms=FieldedSearchList([
                FieldedSearchTerm(operator='AND', field='author',
                                  term='schroder'),
                FieldedSearchTerm(operator='AND', field='title', term='jqk'),
            ])
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set.results), 0)
