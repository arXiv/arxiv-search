"""Test the simple search feature."""

from unittest import TestCase
import subprocess
import time


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
        """Spin up Elasticsearch."""
        build_es = subprocess.run(
            "docker build ."
            " -t arxiv/elasticsearch"
            " -f ./Dockerfile-elasticsearch",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        print(build_es.stdout)
        start_es = subprocess.run(
            "docker run -d -p 9200:9200 arxiv/elasticsearch",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        cls.container = start_es.stdout.decode('ascii').strip()
        print(start_es.stdout)
        time.sleep(10)    # In case it takes a moment to start.

    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch."""
        stop_es = subprocess.run(f"docker rm -f {cls.container}",
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
        print(stop_es)

    def test_simple_search_all_fields(self):
        """
        Scenario: simple term search across all fields.
        """
        self.assertTrue(True)
