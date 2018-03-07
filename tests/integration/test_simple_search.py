"""Test the simple search feature."""

from unittest import TestCase
import os
import subprocess
import time

# os.environ['ELASTICSEARCH_HOST'] = os.environ.get('ELASTICSEARCH_SERVICE_HOST')
from search.services import index
from search.agent.consumer import MetadataRecordProcessor
from search.domain import SimpleQuery


class TestSimpleSearch(TestCase):
    """
    Test the simple search feature.

    Users should be able to enter terms and expressions into a basic search
    box. Users should also be able to select from a simple list of metadata in
    which to search. A list of results is generated containing the results
    across the metadata fields selected.
    """

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
            "docker run -d -p 9200:9200 arxiv/elasticsearch",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        cls.container = start_es.stdout.decode('ascii').strip()

        print('\rWaiting for ES cluster to be available...')
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
            "1408.6682"     # $\lambda$
        ]
        cls.cache_dir = os.path.abspath('tests/data/examples')
        cls.processor = MetadataRecordProcessor()
        cls.processor.init_cache(cls.cache_dir)
        cls.processor.index_papers(to_index)
        time.sleep(5)    # Give a few seconds for docs to be available.

    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch."""
        stop_es = subprocess.run(f"docker rm -f {cls.container}",
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)

    def test_simple_search_all_fields(self):
        """Scenario: simple term search across all fields."""
        # Given search term is "flux capacitor"
        # And selected field to search is "All fields"
        # When a user performs a search...
        query = SimpleQuery(
            raw_query='?searchtype=all&query=flux%20capacitor',
            order='',
            page_size=10,
            field='all',
            value='flux capacitor'
        )
        document_set = index.search(query)
        # All entries contain a metadata field that contains either "flux"
        # or "capacitor".
        self.assertEqual(len(document_set['results']), 3)
        for item in document_set['results']:
            self.assertTrue("flux" in str(item) or "capacitor" in str(item),
                            "Should have a metadata field that contains either"
                            " 'flux' or 'capacitor'.")


    def test_search_for_utf8(self):
        """Scenario: search for TeX terms."""

        # A search for a TeX expression should match similar metadata strings.
        query = SimpleQuery(
            raw_query='?searchtype=all&query=λ',
            order='',
            page_size=10,
            field='all',
            value='λ'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set['results']), 1)
        self.assertEqual(document_set['results'][0]['id'], "1403.6219")

    def test_search_for_texism(self):
        """Scenario: search for TeX terms."""
        query = SimpleQuery(
            raw_query='?query=%24z_1%24&searchtype=all',
            order='',
            page_size=10,
            field='all',
            value='$z_1$'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set['results']), 1)
        self.assertEqual(document_set['results'][0]['id'], "1404.3450")

    def test_search_for_texism2(self):
        """Scenario: search for TeX terms."""
        query = SimpleQuery(
            raw_query='?query=%24%5Clambda%24&searchtype=all',
            order='',
            page_size=10,
            field='all',
            value='$\lambda$'
        )
        document_set = index.search(query)
        self.assertEqual(len(document_set['results']), 2)
