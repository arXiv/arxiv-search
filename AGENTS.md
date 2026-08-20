# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Three Flask apps built from one shared Elasticsearch-backed core, plus indexing scripts:

| App | Factory | Dev entrypoint | Serves |
| --- | --- | --- | --- |
| Search UI | `create_ui_web_app` | `app.py` | `/`, `/advanced`, `/status` — HTML |
| Metadata API | `create_api_web_app` | `api.py` | `/`, `/<paper_id>v<version>` — JSON |
| Classic API | `create_classic_api_web_app` | `classic_api.py` | `/api/query` — Atom XML (the `export.arxiv.org/api/query` replacement) |

All three are defined in `search/factory.py` and deploy independently (`Dockerfile-ui`, `Dockerfile-api`, `Dockerfile-classic-api`; Helm charts in `deploy/`).

## Toolchain

**Poetry, and Python 3.10 specifically.** CI pins 3.10.9.

Python 3.11+ breaks the test suite. `Field`, `Operator`, `SortBy`, `SortDirection` in `search/domain/base.py` are `(str, Enum)` subclasses whose *values* get interpolated into Lucene query strings and ES DSL. 3.11 changed `str.__format__`/`__str__` for such enums to return `Field.Title` instead of `ti`, so query building silently produces garbage and the classic-parser tests fail. Before debugging a mysterious `lark.exceptions.UnexpectedCharacters` on `Field.Title:...`, check `python --version`.

If `poetry env list` shows a 3.11+ interpreter, point it at 3.10 (`poetry env use 3.10`) rather than working around the failures.

`Pipfile`/`Pipfile.lock` are legacy — last touched in 2023, still listing `nose2` and `mypy==0.720`. `pyproject.toml`/`poetry.lock` are what CI and the current Dockerfiles use.

## Commands

```bash
poetry install                      # dev deps included
poetry run pytest                   # full suite; ~100 tests, no Elasticsearch needed (all mocked)
poetry run pytest -q search/domain/classic_api/tests/test_classic_parser.py
poetry run pytest -q search/routes/classic_api/tests/test_classic.py::TestClassicAPISearch::test_query
```

Run a dev server (any of the three apps — swap `FLASK_APP`):

```bash
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_SERVICE_HOST=127.0.0.1 poetry run flask run
```

`python main.py` runs the UI on `:8080` with template auto-reload, no env vars needed.

Local Elasticsearch + Kibana: `docker-compose up` (ES on `:9200`, Kibana on `:5601`). Then populate:

```bash
FLASK_APP=app.py ELASTICSEARCH_SERVICE_HOST=127.0.0.1 poetry run python create_index.py
FLASK_APP=app.py ELASTICSEARCH_SERVICE_HOST=127.0.0.1 poetry run python bulk_index.py
```

`bulk_index.py` with no args indexes `tests/data/sample.json` (several minutes); `--paper_id`/`--id_list` for specific papers. It fetches from the `/docmeta` endpoint, which is **only reachable from the CUL network**. `reindex.py OLD NEW` copies an index under the current mapping; `audit.py -l ids.txt -o missing.txt` finds unindexed papers.

Static checking (goals: mypy/pydocstyle zero, pylint ≥9):

```bash
poetry run mypy -p search | grep -v "test.*" | grep -v "defined here"
poetry run pydocstyle --convention=numpy --add-ignore=D401 search
poetry run pylint search
```

### Test discovery gap

Five test files are named `tests.py`, which pytest's default `test_*.py` pattern does **not** collect, so `poetry run pytest` and CI skip them entirely:

- `search/controllers/advanced/tests.py`, `search/controllers/simple/tests.py`, `search/controllers/tests.py`
- `search/process/tests.py`
- `search/services/index/tests/tests.py`

They are runnable by explicit path (`poetry run pytest search/controllers/advanced/tests.py`) and some currently fail. Treat their coverage as unverified — if you change a controller or `search/process/transform.py`, run its `tests.py` by hand.

## Architecture

Request flow is a strict four-layer stack; each layer speaks only in domain objects:

```
routes/ ──> controllers/ ──> services/index/ ──> Elasticsearch
   │             │                  │
   └─ serialize/ └─ domain/ ────────┘
```

- **`search/routes/`** — blueprints. Parse nothing; hand `request.args` to a controller, get back `(data, status, headers)`, render or serialize. `ui.py` also persists `order`/`size`/`abstracts`/`date-date_type` in the `arxiv-search-parameters` cookie via `before_request`/`after_request`.
- **`search/controllers/`** — one package per feature (`simple`, `advanced`, `api`, `classic_api`). Each exposes a function returning the 3-tuple above, and owns request validation (WTForms in `simple/forms.py`, `advanced/forms.py`) and building a domain `Query`.
- **`search/domain/`** — the shared vocabulary. `SimpleQuery`, `AdvancedQuery`, `APIQuery`, `ClassicAPIQuery` are dataclasses; search *results* (`Document`, `DocumentSet`) are `TypedDict`s. That split is deliberate — see `DECISIONS.md` 2019-04-22: dataclass casting was ~100× the cost of dict init and results are high-volume.
- **`search/services/index/`** — everything Elasticsearch. `SearchSession.search()` dispatches on the query's *type* (`isinstance(query, AdvancedQuery)` → `advanced.py`, `SimpleQuery` → `simple.py`, `APIQuery` → `api.py`, `ClassicAPIQuery` → `classic_api/`). `prepare.py` holds `SEARCH_FIELDS`, the field→query-builder map that all four share; `highlighting.py` amends the query *and* post-processes hits; `authors.py` handles name/ORCID/author-id matching; `results.py` turns an ES response into a `DocumentSet`.
- **`search/serialize/`** — `as_json` (metadata API) and `as_atom` (classic API, via `feedgen` + custom `atom_extensions.py`). Response shapes are pinned by JSON Schema in `schema/resources/`, which the serializer tests validate against.

Indexing (separate from serving): `services/metadata.py` fetches `DocMeta` from the docmeta endpoint → `process/transform.py` maps it to an indexable `Document` → `SearchSession.add_document`/`bulk_add_documents`. Each *version* of a paper is its own ES document (`DECISIONS.md` #6); simple/author search filter to current versions, advanced search does not.

### Things that will surprise you

- **`search/services/index/__init__.py` monkeypatches `elasticsearch.client.Elasticsearch.search`** at import time to issue POST instead of GET, because GCP load balancers reject GET requests carrying a body. It runs before any other import in the module.
- **`ELASTICSEARCH_MAPPING` defaults to the relative path `mappings/DocumentMapping.json`**, so `create_index.py`/`reindex.py` must be run from the repo root.
- **`MAX_RESULTS = 10_000`** (`services/index/util.py`) caps pagination; exceeding it raises `OutsideAllowedRange`.
- **The API endpoints are unauthenticated.** `@scoped(required=scopes.READ_PUBLIC)` is commented out in both `routes/api/__init__.py` and `routes/classic_api/__init__.py`.
- **`TESTING=yes` triggers a live ES check at startup** (`factory.index_startup_check`) that aborts if the cluster, index, or a sample query fails.
- **Config is read once from `os.environ` at import** of `search/config.py`. The WSGI wrappers (`wsgi*.py`) copy the WSGI environ into `os.environ` *before* calling the factory for exactly this reason.

### Classic API compatibility

The classic API is a Python reimplementation of a Perl/Lucene 2.3.2 service, and bug-compatibility with it is a requirement, not a nicety.

- `search/domain/classic_api/query_parser.py` — a `lark` grammar over the documented `search_query` syntax (`au:`, `ti:`, `ANDNOT`, …), producing a `Phrase` tree.
- `search/domain/classic_api/classic_search_query.py` — `adapt_query()`, a pre-parse rewrite pass that repairs queries old Lucene accepted but the grammar rejects (bare `lastUpdatedDate:` aliasing, partial `submittedDate` ranges filled out to 12 digits, stray characters). Controllers call it before parsing; `&raw=1` bypasses it.
- `search/domain/classic_api/README_classic_search_query.md` — the empirical record of how legacy Lucene actually behaved, as ~100 `curl` comparisons against `export.arxiv.org` alongside the local equivalent (default operator is OR, prefix-parens distribute, quotes are phrases but not literal, `submittedDate` matches the Atom `published` element, etc.). Read this before changing query parsing or Atom date fields — it is the spec that the tests encode.

## Stale files — don't follow these

- `README.md` documents `pipenv` and `nose2 --with-coverage`. Both are gone; use poetry + pytest.
- `Makefile` has `PROJECT := feed` (copy-paste from arxiv-feed), so `make format` targets a nonexistent directory; its `test` target calls `nose2`. `make index` and `make index-test` still work if you swap `pipenv run` for `poetry run`.
- `search/agent/` **does not exist** — the Kinesis indexing agent was removed in `68ee63c`. `bin/start_agent.py`, `Dockerfile-agent`, the `agent`/`localstack` services in `docker-compose.yml`, the `KINESIS_*` config block, and the whole "Running the indexing agent" section of the README are all dead references.
- `Dockerfile` and `Dockerfile-api` still build on `arxiv/base:0.16.x` with pipenv. `Dockerfile-ui` and `Dockerfile-classic-api` are the maintained ones.
- `lintstats.sh` posts commit statuses to Travis CI, which is no longer used. GitHub Actions (`.github/workflows/python-app.yml`) runs only `poetry run pytest`; flake8 is commented out there.
- `.pre-commit-config.yaml` pins `black` at `rev: stable` and pydocstyle at `master`, and `black` is not a poetry dependency. Expect `pre-commit install` to need fixing before it works.
- `classic-api.py` and `classic_api.py` are byte-identical duplicates.

`docs/` is Sphinx source published to <https://arxiv.github.io/arxiv-search> by `update-docs.sh`; it is unrelated to the workspace `docs/prs/` work-product convention.
