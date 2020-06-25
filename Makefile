.PHONY: default help index index-test run-classic-api test check format
.DEFAULT_GOAL := help
SHELL := /bin/bash
PROJECT := feed

.EXPORT_ALL_VARIABLES:
PIPENV_VERBOSITY = -1


help:                   ## Show help.
	@grep -E '^[a-zA-Z2_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


# Index

index:                  ## Create and populate elasticsearch index.
	@FLASK_APP=app.py pipenv run python create_index.py
	@FLASK_APP=app.py pipenv run python bulk_index.py


index-test:            ## Test if the index is created.
	@curl http://127.0.0.1:9200/arxiv/_search 2> /dev/null | jq '.hits.hits[]._source | {id: .id, title: .title, arxiv: .primary_classification.category.id}'

# Services

run-classic-api:       ## Run classic feed server in development mode.
	@FLASK_APP=classic_api.py pipenv run flask run


# Utilities

test:                   ## Run tests and coverage checks.
	@pipenv run nose2 -vvv tests.base_app_tests
	@pipenv run nose2 -vvv --with-coverage


check:                  ## Run code checks.
	@bash lintstats.sh


format:                 ## Format the code.
	@pipenv run black --safe --target-version=py37 --line-length=79 "$(PROJECT)"
