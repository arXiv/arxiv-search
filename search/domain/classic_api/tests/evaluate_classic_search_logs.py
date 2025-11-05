# File: evaluate_classic_search_logs.py
# Desc: Read web logs, convert search_query, see if matches api def.
# Use:  PYTHONPATH=. python search/domain/classic_api/tests/evaluate_classic_search_logs.py
# Logs: wc tests/data/example_parse_*_log

import re
import requests
import time
import xml.etree.ElementTree as ET

from urllib.parse import urlparse, parse_qs
from search.domain.classic_api.query_parser import QUERY_PARSER
from lark import Lark, UnexpectedInput

import search.domain.classic_api.classic_search_query as csq


#ACCESS_LOG_FILE = "tests/data/example_access_log"
#ACCESS_LOG_FILE = "tests/data/arxiv-export4_ssl_oct_2_to_16.99.log"
ACCESS_LOG_FILE = "tests/data/arxiv-export4_ssl_oct_2_to_16.log"
FAIL_FILE       = "tests/data/example_fail_log"
FAIL_RES_FILE   = "tests/data/example_fail_res_log"
GOOD_FILE       = "tests/data/example_good_log"
GOOD_RES_FILE   = "tests/data/example_good_res_log"
ERR_RES_FILE    = "tests/data/example_err_res_log"

APACHE_RE = re.compile(r'"(GET|POST|PUT|DELETE|HEAD|OPTIONS) (.*?) HTTP/[\d.]+" \d+ (\d+)')

START_LINE = 4404

OLD_URL = "https://export.arxiv.org/api/query"
NEW_URL = "http://localhost:8080/api/query"

NAMESPACES = {
    'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
    'atom': 'http://www.w3.org/2005/Atom'
}
SLEEP_SEC = 5


with (
    open(ACCESS_LOG_FILE, 'r') as alfile,
    open(GOOD_FILE,     'w') as gfile,
    open(GOOD_RES_FILE, 'w') as grfile,
    open(FAIL_FILE,     'w') as ffile,
    open(FAIL_RES_FILE, 'w') as frfile,
    open(ERR_RES_FILE,  'w') as erfile,
):

    i = 0
    for line in alfile:
        i = i + 1
        if i < START_LINE:
            continue

        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = APACHE_RE.search(line)
        if not match:
            continue

        method = match.group(1)
        full_url = match.group(2)
        log_status = match.group(3)

        print(f"{i}. {log_status}. {full_url}")
        if log_status != "200":
            continue

        parsed_url = urlparse(full_url)
        query_params = parse_qs(parsed_url.query)
        if 'search_query' not in query_params:
            continue

        old_search_query = query_params['search_query'][0]
        new_search_query = csq.adapt_query(old_search_query)

        # Any converted search_query that fails to parse in the
        #   python Lark library, will be logged.
        result = None
        try:
            result = QUERY_PARSER.parse(new_search_query)
            gfile.write(f"{i}\n")
            gfile.write(f"{new_search_query}\n")
            gfile.flush()
        except Exception as e:
            ffile.write(f"{i}\n")
            ffile.write(f"{old_search_query}\n")
            ffile.write(f"{new_search_query}\n")
            ffile.flush()

        if result:
            old_results = 0
            new_results = 0

            old_params = {"search_query" : old_search_query}
            response = requests.get(OLD_URL, params=old_params)
            old_status_code = response.status_code
            if old_status_code == 200:
                xml_content = response.text
                root = ET.fromstring(xml_content)
                old_results = int(root.find('opensearch:totalResults', NAMESPACES).text)
            else:
                old_results = -1

            new_params = {"search_query" : new_search_query}
            response = requests.get(NEW_URL, params=new_params)
            new_status_code = response.status_code
            if new_status_code == 200:
                xml_content = response.text
                root = ET.fromstring(xml_content)
                new_results = int(root.find('opensearch:totalResults', NAMESPACES).text)
            else:
                new_results = -1

            summary = f"{i}. old:{old_status_code}-res:{old_results}; new:{new_status_code}-res:{new_results}"
            print(summary)

            if (old_results == -1 or new_results == -1):
                # Log anytime that a query that does not succeed
                #   in both the perl and the python version.
                # Remember the perl version hides errors that it throws.
                # There may be downtime/rate limiting.
                erfile.write(f"{summary}\n")
                erfile.flush()
            else:
                # The search dbs are expected to return
                #   a different number of results.
                # If the new search returns no results,
                #   log those, to check for issues.
                if (old_results > 0 and new_results == 0):
                    frfile.write(f"{summary}\n")
                    frfile.flush()
                else:
                    grfile.write(f"{summary}\n")
                    grfile.flush()


            print("-" * 40, "completed line:", i)
            time.sleep(SLEEP_SEC)
