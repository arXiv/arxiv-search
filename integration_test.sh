#!/bin/bash
set -o errexit

echo "Waiting for ES to start then creating index..."
FLASK_APP=app.py FLASK_DEBUG=1 pipenv run python create_index.py --wait
echo "ES started and index created"
echo "About to fill the index with the standard bulk dataset..."
FLASK_APP=app.py FLASK_DEBUG=1 pipenv run python bulk_index.py
echo "Done filling index."
echo "About to start integration tests"
WITH_INTEGRATION=True nose2 tests.integration.test_integration
echo "Done with integration tests.

